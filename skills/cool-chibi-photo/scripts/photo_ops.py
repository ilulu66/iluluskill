#!/usr/bin/env python3
"""Local, non-generative photo operations. No network calls and no face recognition.

Python 3.10+. Restore masks: 255=reference, 0=edited background.
Compose masks: any nonzero value means do not cover with the sticker.
Coordinates are pixel coordinates AFTER EXIF orientation correction.
The helper does not make semantic masks, generate chibis, or certify likeness.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageCms, ImageOps


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def load_rgb(path: Path) -> Image.Image:
    """Normalize orientation and, when embedded, ICC profile to sRGB."""
    with Image.open(path) as im:
        im = ImageOps.exif_transpose(im)
        icc = im.info.get('icc_profile')
        if icc:
            try:
                im = ImageCms.profileToProfile(
                    im, ImageCms.ImageCmsProfile(io.BytesIO(icc)),
                    ImageCms.createProfile('sRGB'), outputMode='RGB')
            except Exception as exc:
                raise ValueError(f'Cannot convert ICC profile in {path}; normalize it first.') from exc
        return im.convert('RGB').copy()


def load_mask(path: Path, size: tuple[int, int]) -> np.ndarray:
    with Image.open(path) as im:
        if im.size != size:
            raise ValueError(f'Mask size {im.size} must match oriented reference {size}.')
        # Require explicit grayscale. Never silently use an RGBA alpha mask.
        if im.mode not in ('L', '1'):
            raise ValueError('Mask must be grayscale L/1; see the command for white/black semantics.')
        return np.asarray(im.convert('L')).copy()


def save_png(im: Image.Image, path: Path, overwrite: bool = False) -> None:
    if path.suffix.lower() != '.png':
        raise ValueError('Output must end in .png (lossless master).')
    if path.exists() and not overwrite:
        raise FileExistsError(f'Refusing to overwrite {path}. Use a new output name.')
    path.parent.mkdir(parents=True, exist_ok=True)
    # Do not copy source GPS/EXIF metadata into the derivative.
    profile = ImageCms.ImageCmsProfile(ImageCms.createProfile('sRGB')).tobytes()
    im.save(path, format='PNG', icc_profile=profile)


def save_report(data: dict[str, Any], path: Path, overwrite: bool = False) -> None:
    if path.exists() and not overwrite:
        raise FileExistsError(f'Report already exists: {path}')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def grade_image(im: Image.Image, preset: str, strength: float, exposure: float,
                shadow_lift: float = 0.02) -> Image.Image:
    """Gentle reproducible global grade; NOT automatic skin-aware retouching."""
    if not 0 <= strength <= 1 or not -2 <= exposure <= 2 or not 0 <= shadow_lift <= 0.1:
        raise ValueError('strength: 0..1, exposure EV: -2..2, shadow_lift: 0..0.1')
    if preset not in ('none', 'neutral-cool', 'neutral', 'warm-soft'):
        raise ValueError('Unknown grade preset.')
    if exposure == 0 and (preset == 'none' or strength == 0):
        return im.convert('RGB').copy()
    rgb = np.asarray(im.convert('RGB'), dtype=np.float32) / 255.0
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    linear = np.clip(linear * (2.0 ** exposure), 0, 1)
    out = np.where(linear <= 0.0031308, linear * 12.92,
                   1.055 * np.maximum(linear, 0) ** (1 / 2.4) - 0.055)
    if preset != 'none' and strength > 0:
        lum = out @ np.array([0.2126, 0.7152, 0.0722], dtype=np.float32)
        weight = (1 - lum) ** 2
        # Raise shadow detail without raising true black to gray.
        lift = strength * shadow_lift * weight * np.minimum(lum / 0.08, 1)
        out = out + lift[..., None]
        tint = {'neutral-cool': [-0.010, 0.0, 0.013],
                'neutral': [0.0, 0.0, 0.0],
                'warm-soft': [0.011, 0.002, -0.008]}[preset]
        out = out + strength * weight[..., None] * np.array(tint, dtype=np.float32)
    return Image.fromarray(np.uint8(np.rint(np.clip(out, 0, 1) * 255)))


def restore_pixels(reference: Image.Image, edited: Image.Image, mask: np.ndarray) -> Image.Image:
    if reference.size != edited.size or mask.shape != (reference.height, reference.width):
        raise ValueError('Reference, edited background and keep mask must share the same size/alignment.')
    a = np.asarray(reference.convert('RGB'), dtype=np.float32)
    b = np.asarray(edited.convert('RGB'), dtype=np.float32)
    alpha = mask.astype(np.float32)[..., None] / 255.0
    out = np.rint(a * alpha + b * (1 - alpha)).astype(np.uint8)
    return Image.fromarray(out)


def padding_values(values: list[int]) -> tuple[int, int, int, int]:
    if len(values) != 4 or any(x < 0 for x in values):
        raise ValueError('Padding is four nonnegative pixel values: left top right bottom.')
    return tuple(values)  # type: ignore[return-value]


def pad_image(im: Image.Image, padding: tuple[int, int, int, int]) -> Image.Image:
    if any(v < 0 for v in padding):
        raise ValueError('Padding cannot be negative.')
    return ImageOps.expand(im.convert('RGB'), border=padding, fill='white')


def load_sticker(path: Path) -> Image.Image:
    with Image.open(path) as original:
        im = ImageOps.exif_transpose(original).convert('RGBA')
        alpha = im.getchannel('A')
        amin, amax = alpha.getextrema()
        if amin != 0 or amax == 0:
            raise ValueError('Sticker needs true transparent pixels and visible content. '
                             'Opaque checkerboard/white-background images are not transparent PNGs.')
        bbox = alpha.getbbox()
        if bbox is None:
            raise ValueError('Sticker is empty.')
        return im.crop(bbox).copy()


def validate_boxes(boxes: list[Any], size: tuple[int, int]) -> list[tuple[int, int, int, int]]:
    result = []
    w, h = size
    for box in boxes:
        if not isinstance(box, (list, tuple)) or len(box) != 4:
            raise ValueError('Each protected box must be [left, top, right, bottom].')
        if any(type(v) is not int for v in box):
            raise ValueError('Protected coordinates must be integers, not normalized fractions.')
        l, t, r, b = box
        if not (0 <= l < r <= w and 0 <= t < b <= h):
            raise ValueError(f'Invalid protected box {box} for {size}.')
        result.append((l, t, r, b))
    return result


def overlaps(alpha: Image.Image, xy: tuple[int, int], boxes: list[tuple[int, int, int, int]]) -> bool:
    x, y = xy
    w, h = alpha.size
    for l, t, r, b in boxes:
        ll, tt, rr, bb = max(l, x), max(t, y), min(r, x + w), min(b, y + h)
        if rr > ll and bb > tt:
            if alpha.crop((ll-x, tt-y, rr-x, bb-y)).getbbox() is not None:
                return True
    return False


def compose_image(photo: Image.Image, sticker: Image.Image, *, width_ratio: float = 0.30,
                  min_width_ratio: float = 0.22, max_height_ratio: float = 0.50,
                  margin_ratio: float = 0.035, padding: tuple[int, int, int, int] = (0, 0, 0, 0),
                  crop: tuple[int, int, int, int] | None = None,
                  protect_boxes: list[Any] | None = None,
                  protect_mask: np.ndarray | None = None,
                  max_inset_ratio: float = 0.12,
                  allow_sticker_upscale: bool = False) -> tuple[Image.Image, dict[str, Any]]:
    if not (0 < min_width_ratio <= width_ratio <= 0.75):
        raise ValueError('Need 0 < min_width_ratio <= width_ratio <= 0.75.')
    if not (0.01 <= margin_ratio <= 0.20 and 0 < max_height_ratio <= 0.75):
        raise ValueError('Invalid safe margin or maximum height.')
    if not 0 <= max_inset_ratio <= 0.25:
        raise ValueError('Local bottom-right inset must be between 0 and 0.25.')
    boxes = validate_boxes(protect_boxes or [], photo.size)
    c = crop or (0, 0, photo.width, photo.height)
    validate_boxes([c], photo.size)
    cl, ct, cr, cb = c
    if protect_mask is not None:
        protect_mask = np.asarray(protect_mask)
        if protect_mask.shape != (photo.height, photo.width):
            raise ValueError('Overlay protect mask must match the oriented photo size.')
        if not np.isfinite(protect_mask).all() or protect_mask.min() < 0 or protect_mask.max() > 255:
            raise ValueError('Overlay protect mask values must be 0..255.')
        protect_mask = protect_mask > 0
        if np.count_nonzero(protect_mask) != np.count_nonzero(protect_mask[ct:cb, cl:cr]):
            raise ValueError('Crop would remove protected mask pixels.')
    for l, t, r, b in boxes:
        if l < cl or t < ct or r > cr or b > cb:
            raise ValueError('Crop would remove a protected face/body/hand/prop. Revise crop.')
    pl, pt, pr, pb = padding
    base = pad_image(photo.crop(c), padding)
    mapped = [(l-cl+pl, t-ct+pt, r-cl+pl, b-ct+pt) for l, t, r, b in boxes]
    w, h = base.size
    blocked = np.zeros((h, w), dtype=bool)
    if protect_mask is not None:
        blocked[pt:pt+cb-ct, pl:pl+cr-cl] = protect_mask[ct:cb, cl:cr]
    for l, t, r, b in mapped:
        blocked[t:b, l:r] = True
    margin = max(1, round(min(w, h) * margin_ratio))
    aspect = sticker.height / sticker.width
    desired_w = min(round(w * width_ratio), round(h * max_height_ratio / aspect), w-2*margin)
    min_w = max(1, round(w * min_width_ratio))
    if not allow_sticker_upscale:
        desired_w = min(desired_w, sticker.width)
    if desired_w < min_w:
        raise ValueError('Sticker resolution/aspect cannot meet minimum readable size. '
                         'Generate a larger or more compact sticker; do not claim interpolation restores detail.')
    # Keep the readable size first, then search nearby positions; shrink only
    # after the local alternatives at that size have been exhausted.
    step = max(1, round(min(w, h) * 0.02))
    max_dx, max_dy = round(w * max_inset_ratio), round(h * max_inset_ratio)
    xs = sorted(set(range(0, max_dx + 1, step)) | {max_dx})
    ys = sorted(set(range(0, max_dy + 1, step)) | {max_dy})
    offsets = sorted(((dx, dy) for dx in xs for dy in ys), key=lambda p: (sum(p), p[1], p[0]))
    widths = list(range(desired_w, min_w - 1, -max(1, desired_w // 100)))
    if not widths or widths[-1] != min_w:
        widths.append(min_w)
    selected = None
    for sw in widths:
        sh = max(1, round(sw * aspect))
        patch = sticker.resize((sw, sh), Image.Resampling.LANCZOS)
        visible = np.asarray(patch.getchannel('A')) > 0
        for dx, dy in offsets:
            x, y = w-margin-sw-dx, h-margin-sh-dy
            if x < margin or y < margin:
                continue
            if not np.any(visible & blocked[y:y+sh, x:x+sw]):
                selected = (patch, x, y)
                break
        if selected is not None:
            break
    if selected is None:
        raise ValueError('No readable bottom-right placement at the minimum width. '
                         'Review hard exclusion zones, simplify nonessential props, or use authorized reframing/padding.')
    patch, x, y = selected
    out = base.convert('RGBA')
    out.alpha_composite(patch, (x, y))
    out = out.convert('RGB')
    original_array, final_array = np.asarray(base), np.asarray(out)
    protected_equal = bool(np.array_equal(original_array[blocked], final_array[blocked]))
    info: dict[str, Any] = {
        'source_oriented_size': list(photo.size), 'output_size': list(out.size),
        'crop_ltrb': list(c), 'padding_ltrb_px': list(padding),
        'sticker_bbox_ltrb': [x, y, x+patch.width, y+patch.height],
        'sticker_width_ratio': round(patch.width / w, 5), 'safe_margin_px': margin,
        'minimum_width_ratio': min_width_ratio,
        'inset_right_bottom_px': [w-margin-x-patch.width, h-margin-y-patch.height],
        'sticker_upscaled': patch.width > sticker.width,
        'protected_box_count': len(mapped),
        'protected_pixel_count': int(np.count_nonzero(blocked)),
        'protected_pixels_equal_to_supplied_base': protected_equal if np.any(blocked) else None,
        'semantic_identity_count_outfit_anatomy': 'not_checked_requires_visual_review',
        'note': 'Checks concern supplied base and overlay exclusion areas only. '
                'They do not prove scene, pose, style, proportions, or user acceptance.'
    }
    return out, info


def verify_pixels(reference: Image.Image, candidate: Image.Image, mask: np.ndarray) -> dict[str, Any]:
    if reference.size != candidate.size or mask.shape != (reference.height, reference.width):
        raise ValueError('Pixel lock verification needs equal dimensions and registered coordinates.')
    selected = mask == 255
    count = int(np.count_nonzero(selected))
    if count == 0:
        raise ValueError('No fully protected pixels (mask==255). An empty/soft-only mask cannot certify a lock.')
    a = np.asarray(reference.convert('RGB')).astype(np.int16)
    b = np.asarray(candidate.convert('RGB')).astype(np.int16)
    delta = np.abs(a[selected] - b[selected])
    changed = int(np.count_nonzero(np.any(delta != 0, axis=1)))
    return {'protected_pixel_count': count, 'changed_pixel_count': changed,
            'max_channel_difference': int(delta.max()),
            'mean_channel_difference': float(delta.mean()), 'pixel_lock_pass': changed == 0,
            'scope': 'Only supplied mask==255 pixels; no biometric or semantic validation.'}


def add_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--overwrite', action='store_true', help='Only for derivative outputs, never source files.')


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    g = sub.add_parser('grade', help='Deterministic mild color/exposure, no generative editing.')
    g.add_argument('--input', type=Path, required=True)
    g.add_argument('--preset', choices=['none', 'neutral-cool', 'neutral', 'warm-soft'], default='neutral-cool')
    g.add_argument('--strength', type=float, default=0.35)
    g.add_argument('--exposure', type=float, default=0.0, help='Exposure compensation in EV.')
    g.add_argument('--shadow-lift', type=float, default=0.02)
    g.add_argument('--protect-mask', type=Path, help='Keep mask==255 core RGB unchanged.')
    add_output(g)
    r = sub.add_parser('restore', help='Composite original foreground back over edited background.')
    r.add_argument('--reference', type=Path, required=True)
    r.add_argument('--edited', type=Path, required=True)
    r.add_argument('--keep-mask', type=Path, required=True)
    add_output(r)
    c = sub.add_parser('compose', help='Place true-alpha sticker at bottom right with exclusion boxes/mask.')
    c.add_argument('--photo', type=Path, required=True)
    c.add_argument('--sticker', type=Path, required=True)
    c.add_argument('--width-ratio', type=float, default=0.30)
    c.add_argument('--min-width-ratio', type=float, default=0.22)
    c.add_argument('--max-height-ratio', type=float, default=0.50)
    c.add_argument('--margin-ratio', type=float, default=0.035)
    c.add_argument('--padding', type=int, nargs=4, default=[0, 0, 0, 0], metavar=('LEFT', 'TOP', 'RIGHT', 'BOTTOM'))
    c.add_argument('--crop', type=int, nargs=4, metavar=('LEFT', 'TOP', 'RIGHT', 'BOTTOM'))
    c.add_argument('--protect-json', type=Path)
    c.add_argument('--protect-mask', type=Path, help='Grayscale overlay exclusion mask; nonzero means do not cover. Not a foreground-restore mask.')
    c.add_argument('--max-inset-ratio', type=float, default=0.12, help='Search locally inward from bottom right before reducing size; 0 disables movement.')
    c.add_argument('--allow-sticker-upscale', action='store_true')
    add_output(c)
    pad = sub.add_parser('pad', help='Add white canvas only; do not scale or regenerate existing picture.')
    pad.add_argument('--input', type=Path, required=True)
    pad.add_argument('--padding', type=int, nargs=4, required=True)
    add_output(pad)
    v = sub.add_parser('verify-lock', help='Check exact RGB preservation inside a supplied keep mask.')
    v.add_argument('--reference', type=Path, required=True)
    v.add_argument('--candidate', type=Path, required=True)
    v.add_argument('--keep-mask', type=Path, required=True)
    v.add_argument('--report', type=Path, required=True)
    args = p.parse_args()
    try:
        output = getattr(args, 'output', None)
        inputs = [getattr(args, n, None) for n in ('input', 'reference', 'edited', 'photo', 'sticker', 'candidate', 'keep_mask', 'protect_mask', 'protect_json')]
        destinations = [output, getattr(args, 'report', None)]
        if args.command == 'compose':
            destinations.append(args.output.with_suffix('.layout.json'))
        for destination in destinations:
            if destination is not None and any(isinstance(i, Path) and i.resolve() == destination.resolve() for i in inputs):
                raise ValueError('Never overwrite input/reference/mask files with an image or report, even with --overwrite.')
        if args.command == 'grade':
            im = load_rgb(args.input)
            out = grade_image(im, args.preset, args.strength, args.exposure, args.shadow_lift)
            if args.protect_mask:
                out = restore_pixels(im, out, load_mask(args.protect_mask, im.size))
            save_png(out, args.output, args.overwrite)
        elif args.command == 'restore':
            im = load_rgb(args.reference)
            out = restore_pixels(im, load_rgb(args.edited), load_mask(args.keep_mask, im.size))
            save_png(out, args.output, args.overwrite)
        elif args.command == 'pad':
            save_png(pad_image(load_rgb(args.input), padding_values(args.padding)), args.output, args.overwrite)
        elif args.command == 'compose':
            boxes = []
            if args.protect_json:
                data = json.loads(args.protect_json.read_text(encoding='utf-8'))
                boxes = data['protect_boxes']
                if not isinstance(boxes, list) or not boxes:
                    raise ValueError('Supplied protect-json must contain a nonempty protect_boxes list.')
            report_path = args.output.with_suffix('.layout.json')
            if report_path.exists() and not args.overwrite:
                raise FileExistsError(f'Layout report exists: {report_path}')
            photo = load_rgb(args.photo)
            overlay_mask = load_mask(args.protect_mask, photo.size) if args.protect_mask else None
            out, report = compose_image(
                photo, load_sticker(args.sticker),
                width_ratio=args.width_ratio, min_width_ratio=args.min_width_ratio,
                max_height_ratio=args.max_height_ratio, margin_ratio=args.margin_ratio,
                padding=padding_values(args.padding), crop=tuple(args.crop) if args.crop else None,
                protect_boxes=boxes, protect_mask=overlay_mask, max_inset_ratio=args.max_inset_ratio,
                allow_sticker_upscale=args.allow_sticker_upscale)
            report.update({'photo_path': str(args.photo), 'photo_sha256': sha256(args.photo),
                           'sticker_path': str(args.sticker), 'sticker_sha256': sha256(args.sticker)})
            save_png(out, args.output, args.overwrite)
            save_report(report, report_path, args.overwrite)
        else:
            im = load_rgb(args.reference)
            report = verify_pixels(im, load_rgb(args.candidate), load_mask(args.keep_mask, im.size))
            save_report(report, args.report)
            print(json.dumps(report, ensure_ascii=False, indent=2))
            return 0 if report['pixel_lock_pass'] else 1
        print(f'Saved: {args.output}')
        return 0
    except (ValueError, FileExistsError, FileNotFoundError, KeyError, TypeError, OSError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
