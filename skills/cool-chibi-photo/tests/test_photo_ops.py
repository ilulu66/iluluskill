from __future__ import annotations
import importlib.util
import json
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('photo_ops', ROOT / 'scripts/photo_ops.py')
ops = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ops)

class PhotoOpsTests(unittest.TestCase):
    def setUp(self):
        self.photo = Image.fromarray(np.random.default_rng(8).integers(0, 256, (240, 320, 3), dtype=np.uint8))
        self.sticker = Image.new('RGBA', (180, 180), (10, 90, 150, 255))

    def test_none_is_exact(self):
        self.assertTrue(np.array_equal(np.asarray(self.photo), np.asarray(ops.grade_image(self.photo, 'none', .8, 0))))

    def test_zero_strength_is_exact(self):
        self.assertEqual(self.photo.tobytes(), ops.grade_image(self.photo, 'neutral-cool', 0, 0).tobytes())

    def test_grade_shape_and_change(self):
        result = ops.grade_image(self.photo, 'neutral-cool', .5, .12)
        self.assertEqual(result.size, self.photo.size)
        self.assertNotEqual(result.tobytes(), self.photo.tobytes())

    def test_invalid_grade_parameters(self):
        with self.assertRaises(ValueError):
            ops.grade_image(self.photo, 'neutral', 3, 0)

    def test_restore_core_exact(self):
        mask = np.zeros((240, 320), dtype=np.uint8)
        mask[60:130, 40:170] = 255
        edited = Image.new('RGB', self.photo.size, (0, 0, 0))
        out = ops.restore_pixels(self.photo, edited, mask)
        report = ops.verify_pixels(self.photo, out, mask)
        self.assertTrue(report['pixel_lock_pass'])
        self.assertEqual(out.getpixel((300, 200)), (0, 0, 0))

    def test_restore_soft_edge(self):
        ref, edited = Image.new('RGB', (2, 2), 'white'), Image.new('RGB', (2, 2), 'black')
        out = ops.restore_pixels(ref, edited, np.full((2, 2), 128, dtype=np.uint8))
        self.assertEqual(out.getpixel((0, 0)), (128, 128, 128))

    def test_verify_change_detected(self):
        mask = np.full((240, 320), 255, dtype=np.uint8)
        altered = self.photo.copy()
        px = altered.getpixel((0, 0))
        altered.putpixel((0, 0), ((px[0]+1) % 256, px[1], px[2]))
        report = ops.verify_pixels(self.photo, altered, mask)
        self.assertFalse(report['pixel_lock_pass'])
        self.assertEqual(report['changed_pixel_count'], 1)

    def test_empty_mask_rejected(self):
        with self.assertRaises(ValueError):
            ops.verify_pixels(self.photo, self.photo, np.zeros((240, 320), dtype=np.uint8))

    def test_dimension_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            ops.restore_pixels(self.photo, Image.new('RGB', (10, 10)), np.zeros((240, 320), dtype=np.uint8))

    def test_padding_no_resample(self):
        out = ops.pad_image(self.photo, (10, 12, 90, 20))
        self.assertEqual(out.size, (420, 272))
        self.assertEqual(out.crop((10, 12, 330, 252)).tobytes(), self.photo.tobytes())
        self.assertEqual(out.getpixel((419, 270)), (255, 255, 255))

    def test_compose_safe_margin(self):
        out, report = ops.compose_image(self.photo, self.sticker)
        l, t, r, b = report['sticker_bbox_ltrb']
        self.assertGreaterEqual(out.width-r, report['safe_margin_px'])
        self.assertGreaterEqual(out.height-b, report['safe_margin_px'])
        self.assertEqual(report['protected_pixels_equal_to_supplied_base'], None)
        self.assertEqual(out.crop((0, 0, l, 240)).tobytes(), self.photo.crop((0, 0, l, 240)).tobytes())

    def test_protected_zone_blocks(self):
        with self.assertRaises(ValueError):
            ops.compose_image(self.photo, self.sticker, protect_boxes=[[0, 0, 320, 240]])

    def test_padding_resolves_conflict(self):
        out, report = ops.compose_image(self.photo, self.sticker, padding=(0, 0, 180, 0), protect_boxes=[[0, 0, 320, 240]])
        self.assertTrue(report['protected_pixels_equal_to_supplied_base'])
        self.assertEqual(out.crop((0, 0, 320, 240)).tobytes(), self.photo.tobytes())

    def test_crop_rejects_lost_subject(self):
        with self.assertRaises(ValueError):
            ops.compose_image(self.photo, self.sticker, crop=(80, 0, 320, 240), protect_boxes=[[10, 10, 100, 100]])

    def test_true_alpha_check(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d)/'sticker.png'
            self.sticker.save(f)
            with self.assertRaises(ValueError):
                ops.load_sticker(f)
            sticker = self.sticker.copy()
            sticker.putpixel((0, 0), (0, 0, 0, 0))
            sticker.save(f)
            self.assertEqual(ops.load_sticker(f).mode, 'RGBA')

    def test_local_inset_keeps_readable_target_size(self):
        mask = np.zeros((240, 320), dtype=np.uint8)
        mask[:, 300:] = 255
        out, report = ops.compose_image(self.photo, self.sticker, protect_mask=mask)
        self.assertEqual(report['sticker_width_ratio'], .30)
        self.assertGreater(report['inset_right_bottom_px'][0], 0)
        self.assertTrue(np.array_equal(np.asarray(out)[mask > 0], np.asarray(self.photo)[mask > 0]))
        with self.assertRaises(ValueError):
            ops.compose_image(self.photo, self.sticker, protect_mask=mask, max_inset_ratio=0)

    def test_minimum_readable_size_not_silently_violated(self):
        mask = np.full((240, 320), 255, dtype=np.uint8)
        mask[172:232, 252:312] = 0  # Only a 60px gap, smaller than 22% of 320.
        with self.assertRaisesRegex(ValueError, 'minimum width'):
            ops.compose_image(self.photo, self.sticker, protect_mask=mask)

    def test_overlay_mask_crop_and_padding_coordinates(self):
        mask = np.zeros((240, 320), dtype=np.uint8)
        mask[20:45, 50:90] = 1  # Nonzero, not just 255, is excluded.
        out, report = ops.compose_image(self.photo, self.sticker, protect_mask=mask,
                                        crop=(20, 10, 320, 240), padding=(5, 7, 40, 10))
        mapped = (35, 17, 75, 42)
        self.assertEqual(out.crop(mapped).tobytes(), self.photo.crop((50, 20, 90, 45)).tobytes())
        self.assertEqual(report['protected_pixel_count'], 1000)
        self.assertTrue(report['protected_pixels_equal_to_supplied_base'])

    def test_crop_rejects_lost_overlay_mask(self):
        mask = np.zeros((240, 320), dtype=np.uint8)
        mask[20, 10] = 255
        with self.assertRaisesRegex(ValueError, 'Crop would remove'):
            ops.compose_image(self.photo, self.sticker, protect_mask=mask, crop=(20, 0, 320, 240))

    def test_overlay_mask_invalid_inputs(self):
        masks = [np.zeros((10, 10)), np.full((240, 320), -1),
                 np.full((240, 320), 256), np.full((240, 320), np.nan)]
        for mask in masks:
            with self.subTest(shape=mask.shape, first=mask.flat[0]):
                with self.assertRaises(ValueError):
                    ops.compose_image(self.photo, self.sticker, protect_mask=mask)

    def test_overlay_mask_and_boxes_union(self):
        mask = np.zeros((240, 320), dtype=np.uint8)
        mask[20:40, 200:220] = 255
        out, report = ops.compose_image(self.photo, self.sticker, protect_mask=mask,
                                        protect_boxes=[[10, 10, 30, 30]])
        self.assertEqual(report['protected_pixel_count'], 800)
        self.assertEqual(out.crop((10, 10, 30, 30)).tobytes(), self.photo.crop((10, 10, 30, 30)).tobytes())
        self.assertTrue(np.array_equal(np.asarray(out)[mask > 0], np.asarray(self.photo)[mask > 0]))

    def test_transparent_sticker_region_can_cross_exclusion(self):
        sticker = Image.new('RGBA', (96, 96), (0, 0, 0, 0))
        sticker.paste((10, 90, 150, 255), (0, 0, 30, 96))
        mask = np.zeros((240, 320), dtype=np.uint8)
        mask[:, 300:] = 255
        out, report = ops.compose_image(self.photo, sticker, protect_mask=mask, max_inset_ratio=0)
        self.assertEqual(report['inset_right_bottom_px'], [0, 0])
        self.assertTrue(report['protected_pixels_equal_to_supplied_base'])

    def test_cli_overlay_mask_and_report(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            self.photo.save(directory/'photo.png')
            sticker = self.sticker.copy()
            sticker.putpixel((0, 0), (0, 0, 0, 0))
            sticker.save(directory/'sticker.png')
            mask = np.zeros((240, 320), dtype=np.uint8)
            mask[:, 300:] = 255
            Image.fromarray(mask).save(directory/'mask.png')
            run = subprocess.run([sys.executable, str(ROOT/'scripts/photo_ops.py'), 'compose',
                                  '--photo', str(directory/'photo.png'), '--sticker', str(directory/'sticker.png'),
                                  '--protect-mask', str(directory/'mask.png'), '--output', str(directory/'out.png')],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            report = json.loads((directory/'out.layout.json').read_text())
            self.assertEqual(report['sticker_width_ratio'], .30)
            with Image.open(directory/'out.png') as out:
                self.assertTrue(np.array_equal(np.asarray(out)[mask > 0], np.asarray(self.photo)[mask > 0]))

    def test_overwrite_denied(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d)/'base.png'
            ops.save_png(self.photo, f)
            with self.assertRaises(FileExistsError):
                ops.save_png(self.photo, f)

    def test_cli_help(self):
        run = subprocess.run([sys.executable, str(ROOT/'scripts/photo_ops.py'), '--help'], capture_output=True, text=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn('verify-lock', run.stdout)

    def test_layout_report_cannot_overwrite_protection_input(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            self.photo.save(directory/'photo.png')
            sticker = self.sticker.copy()
            sticker.putpixel((0, 0), (0, 0, 0, 0))
            sticker.save(directory/'sticker.png')
            protection = directory/'out.layout.json'
            contents = '{"protect_boxes": [[10, 10, 30, 30]]}'
            protection.write_text(contents)
            run = subprocess.run([sys.executable, str(ROOT/'scripts/photo_ops.py'), 'compose',
                                  '--photo', str(directory/'photo.png'), '--sticker', str(directory/'sticker.png'),
                                  '--protect-json', str(protection), '--output', str(directory/'out.png'), '--overwrite'],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 2, run.stderr)
            self.assertEqual(protection.read_text(), contents)
            self.assertFalse((directory/'out.png').exists())

    def test_install_excludes_local_runtime_and_private_files(self):
        with tempfile.TemporaryDirectory() as d:
            directory = Path(d)
            source = directory/'source/cool-chibi-photo'
            shutil.copytree(ROOT, source, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            for relative in ['.env', '.venv/marker', 'work/private.png', 'input/photo.jpg', 'output/final.png', '00-协作台账.md']:
                path = source/relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text('local-only fixture')
            project = directory/'project'
            run = subprocess.run([sys.executable, str(source/'scripts/install.py'), '--project', str(project)],
                                 capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stderr)
            target = project/'.agents/skills/cool-chibi-photo'
            self.assertTrue((target/'SKILL.md').is_file())
            self.assertTrue((target/'scripts/photo_ops.py').is_file())
            for relative in ['.env', '.venv', 'work', 'input', 'output', '00-协作台账.md']:
                self.assertFalse((target/relative).exists(), relative)

    def test_install_backup(self):
        with tempfile.TemporaryDirectory() as d:
            project = Path(d)/'project'
            cmd = [sys.executable, str(ROOT/'scripts/install.py'), '--project', str(project)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            target = project/'.agents/skills/cool-chibi-photo'
            self.assertTrue((target/'SKILL.md').is_file())
            self.assertFalse((target/'00-协作台账.md').exists())
            refused = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(refused.returncode, 0)
            second = subprocess.run(cmd+['--replace'], capture_output=True, text=True)
            self.assertEqual(second.returncode, 0, second.stderr)
            backups = list((project/'.agents/skill-backups').glob('cool-chibi-photo_*'))
            self.assertEqual(len(backups), 1)
            self.assertTrue((backups[0]/'SKILL.md').is_file())

if __name__ == '__main__':
    unittest.main()
