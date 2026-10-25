"""Offline routing/archival tests, not image generation or visual acceptance tests."""
from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock
import zlib


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "codex_job.py"
spec = importlib.util.spec_from_file_location("codex_job", SCRIPT)
ops = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(ops)


def make_png(path: Path, *, width: int = 3, height: int = 2,
             rgba: tuple[int, int, int, int] = (20, 40, 60, 255), alpha: bool = True) -> None:
    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
    color = bytes(rgba if alpha else rgba[:3])
    pixels = (b"\0" + color * width) * height
    header = struct.pack(">IIBBBBB", width, height, 8, 6 if alpha else 2, 0, 0, 0)
    path.write_bytes(ops.PNG_SIGNATURE + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels)) + chunk(b"IEND", b""))


class CodexJobTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.source = self.base / "source.png"
        make_png(self.source)
        self.spec_path = self.base / "job-spec.json"
        self.output = self.base / "run"
        self.config = {"source_photo": "source.png", "output_dir": "run",
                       "scenario": "standard", "scene_intent": "人在桌前工作，另一只手比耶。",
                       "subject_details": "只按当前原片的可见衣服和动作，不设计固定服装。",
                       "inputs_reviewed": True, "references": []}
        self.assets = self.base / "package-assets"
        self.assets.mkdir()
        self.builtin_image = self.assets / "lulu-q-style.png"
        make_png(self.builtin_image, width=12, height=9)
        self.metadata = {"id": "lulu-q-style-v1", "image": "lulu-q-style.png",
                         "sha256": ops.digest(self.builtin_image), "use_for": "只参考圆润短身的绘画语言",
                         "default_instructions": "保持清楚柔和的角色绘制，不迁入参考人物身份。"}
        self.metadata_path = self.assets / "default-style.json"
        self.metadata_path.write_text(json.dumps(self.metadata, ensure_ascii=False), encoding="utf-8")
        patcher = mock.patch.object(ops, "BUILTIN_ASSETS_DIR", self.assets)
        patcher.start()
        self.addCleanup(patcher.stop)

    def planning(self, **changes):
        config = {**self.config, **changes}
        self.spec_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")
        return ops.plan(self.spec_path)

    def read(self, name):
        return json.loads((self.output / name).read_text(encoding="utf-8"))

    def generated(self, *, alpha=True):
        path = self.base / "generated.png"
        make_png(path, width=4, height=3, rgba=(80, 30, 40, 0 if alpha else 255), alpha=alpha)
        # APFS supports ns; explicit post-plan timestamp avoids coarse CI FS clocks.
        stamp = max(time.time_ns(), self.read("job.json")["created_at_ns"] + 1)
        os.utime(path, ns=(stamp, stamp))
        return path

    def test_standard_request_exact_schema_and_defaults(self):
        report = self.planning()
        request, job = self.read("imagegen-request.json"), self.read("job.json")
        self.assertEqual(set(request), {"prompt", "referenced_image_paths", "transparent_background"})
        self.assertEqual(report["status"], "planned")
        self.assertEqual(request["referenced_image_paths"], [str(self.source.resolve()), str(self.builtin_image)])
        self.assertFalse(request["transparent_background"])
        self.assertEqual(job["options"]["placement"], "corner")
        self.assertEqual(job["options"]["entry_mode"], "auto")
        self.assertEqual(job["options"]["scene_choice"], "")
        self.assertEqual(job["options"]["background_render_style"], "photo")
        self.assertEqual(job["options"]["decoration"], "clean")
        self.assertFalse(job["options"]["add_text"])
        self.assertEqual(job["generation"]["state"], "not_run")
        self.assertIn("不固定成双人", request["prompt"])
        self.assertIn("不声称像素锁定", request["prompt"])
        self.assertEqual((self.output / "prompt.txt").read_text(encoding="utf-8"), request["prompt"])

    def test_builtin_default_is_an_actual_style_reference_not_a_private_identity(self):
        self.planning()
        request, job = self.read("imagegen-request.json"), self.read("job.json")
        self.assertEqual(job["style_source"], "builtin_reference")
        self.assertIsNone(job["profile_path"])
        self.assertEqual(len(job["references"]), 1)
        reference = job["references"][0]
        self.assertEqual(reference["id"], "lulu-q-style-v1")
        self.assertEqual(reference["role"], "style")
        self.assertEqual(reference["origin"], "builtin_default")
        self.assertEqual(reference["sha256"], ops.digest(self.builtin_image))
        self.assertIn(reference["path"], request["referenced_image_paths"])
        self.assertIn("图2参考角色=style", request["prompt"])
        self.assertIn("不借Lulu的身份、发型、肤色、服装、动作、表情、人数或文字", request["prompt"])
        self.assertIn("二维彩色Q版", request["prompt"])
        self.assertIn("线条干净统一，柔和体积阴影", request["prompt"])
        self.assertIn("约两头身", request["prompt"])
        self.assertIn("自然展开身体高（下巴至脚底）约1:1", request["prompt"])
        self.assertIn(self.metadata["default_instructions"], request["prompt"])
        self.assertEqual(set(request), {"prompt", "referenced_image_paths", "transparent_background"})

    def test_auto_and_standard_entries_use_agent_scenario_without_scene_picker(self):
        for entry in ["auto", "standard"]:
            for scenario in ["no_person", "pet_object"]:
                with self.subTest(entry=entry, scenario=scenario):
                    self.output = self.base / f"{entry}-{scenario}"
                    report = self.planning(entry_mode=entry, scenario=scenario, output_dir=str(self.output))
                    self.assertEqual(report["status"], "planned")
                    self.assertEqual(self.read("job.json")["options"]["scenario"], scenario)
                    self.assertFalse((self.output / "scene-picker.json").exists())
                    self.assertIsNone(report["scene_picker"])
                    self.assertTrue((self.output / "imagegen-request.json").is_file())

    def test_explicit_scene_entry_without_answer_only_creates_three_choice_picker_and_job(self):
        report = self.planning(entry_mode="scene")
        job, picker = self.read("job.json"), self.read("scene-picker.json")
        self.assertEqual(report["status"], "scene_choice_needed")
        self.assertIsNone(report["request"])
        self.assertEqual({path.name for path in self.output.iterdir()}, {"job.json", "scene-picker.json"})
        self.assertEqual(set(picker), {"questions"})
        self.assertEqual(len(picker["questions"]), 1)
        question = picker["questions"][0]
        self.assertEqual(set(question), {"title", "options"})
        self.assertEqual(len(question["options"]), 3)
        self.assertEqual([item.split("：")[0] for item in question["options"]], ["没拍到我", "宠物小物互动", "人太小替换"])
        self.assertIn("never pick the first option or proceed on timeout", job["next_action"])
        self.assertIn("ordinary text", job["next_action"])
        with self.assertRaisesRegex(ValueError, "executable"):
            ops.collect(self.output / "job.json", self.source)

    def test_answered_scene_overrides_scenario_and_does_not_ask_again(self):
        self.planning(entry_mode="scene", scene_choice="pet_object", scenario="standard")
        job = self.read("job.json")
        self.assertEqual(job["status"], "planned")
        self.assertEqual(job["options"]["scenario"], "pet_object")
        self.assertEqual(job["options"]["placement"], "in_scene")
        self.assertEqual(job["options"]["entry_mode"], "scene")
        self.assertEqual(job["options"]["scene_choice"], "pet_object")
        self.assertIn("场景 pet_object", self.read("imagegen-request.json")["prompt"])
        self.assertFalse((self.output / "scene-picker.json").exists())

    def test_replacement_scene_choice_never_invents_permission(self):
        self.planning(entry_mode="scene", scene_choice="small_person")
        job = self.read("job.json")
        self.assertEqual(job["status"], "recommendation_needed")
        self.assertFalse(job["options"]["replace_real_person"])
        self.assertEqual(job["options"]["scenario"], "small_person")
        self.assertFalse((self.output / "scene-picker.json").exists())
        self.assertFalse((self.output / "imagegen-request.json").exists())

    def test_answered_replacement_scene_runs_only_with_explicit_permission(self):
        self.planning(entry_mode="scene", scene_choice="small_person", replace_real_person=True)
        job = self.read("job.json")
        self.assertEqual(job["status"], "planned")
        self.assertTrue(job["options"]["replace_real_person"])
        self.assertIn("场景 small_person", self.read("imagegen-request.json")["prompt"])
        self.assertFalse((self.output / "scene-picker.json").exists())

    def test_invalid_entry_or_scene_choice_is_rejected_before_output(self):
        for changes in [{"entry_mode": "guess"}, {"entry_mode": "scene", "scene_choice": "standard"},
                        {"entry_mode": "auto", "scene_choice": "pet_object"},
                        {"entry_mode": "standard", "scene_choice": "no_person"}]:
            with self.subTest(config=changes), self.assertRaises(ValueError):
                self.planning(**changes)
        self.assertFalse(self.output.exists())

    def test_scene_choice_precedes_style_choice_and_keeps_both_independent(self):
        self.planning(entry_mode="scene", style_selection="needed")
        waiting_job = self.output / "job.json"
        before = waiting_job.read_bytes()
        self.assertEqual(self.read("job.json")["status"], "scene_choice_needed")
        self.assertEqual(self.read("job.json")["options"]["style_selection"], "needed")
        self.assertFalse((self.output / "style-picker.json").exists())
        self.output = self.base / "answered-scene"
        self.planning(output_dir=str(self.output), entry_mode="scene", scene_choice="no_person",
                      style_selection="needed", style_options=[{"id": "a", "label": "A"}, {"id": "b", "label": "B"}])
        self.assertEqual(self.read("job.json")["status"], "style_choice_needed")
        self.assertTrue((self.output / "style-picker.json").exists())
        self.assertFalse((self.output / "scene-picker.json").exists())
        self.assertFalse((self.output / "imagegen-request.json").exists())
        self.assertFalse(self.read("job.json")["options"]["replace_real_person"])
        self.assertEqual(waiting_job.read_bytes(), before)

    def test_auto_detected_small_person_still_requires_explicit_replacement_permission(self):
        self.planning(entry_mode="auto", scenario="small_person")
        job = self.read("job.json")
        self.assertEqual(job["status"], "recommendation_needed")
        self.assertFalse(job["options"]["replace_real_person"])
        self.assertFalse((self.output / "scene-picker.json").exists())
        self.assertFalse((self.output / "imagegen-request.json").exists())

    def test_explicit_style_skips_builtin_even_when_packaged_metadata_is_missing(self):
        self.metadata_path.unlink()
        ref = self.base / "custom-style.png"
        make_png(ref, width=8)
        self.planning(references=[{"path": str(ref), "role": "style", "use_for": "仅采用用户明确的3D角色画法"}])
        request, job = self.read("imagegen-request.json"), self.read("job.json")
        self.assertEqual(job["style_source"], "explicit_reference")
        self.assertEqual(request["referenced_image_paths"], [str(self.source), str(ref)])
        self.assertNotIn("通用默认画风：", request["prompt"])
        self.assertNotIn("内置画风补充：", request["prompt"])

    def test_explicit_style_text_skips_builtin_and_conflicting_default(self):
        self.metadata_path.unlink()
        instructions = "使用用户明确指定的3D黏土质感、三头身设计"
        self.planning(style_instructions=instructions)
        request, job = self.read("imagegen-request.json"), self.read("job.json")
        self.assertEqual(job["style_source"], "explicit_text")
        self.assertEqual(request["referenced_image_paths"], [str(self.source)])
        self.assertIn(instructions, request["prompt"])
        self.assertNotIn("通用默认画风：", request["prompt"])
        self.assertNotIn("约1:1", request["prompt"])
        self.assertNotIn("builtin_default", json.dumps(job["references"]))

    def test_explicit_text_has_priority_with_a_selected_style_reference(self):
        ref = self.base / "custom.png"
        make_png(ref, width=7)
        self.planning(style_instructions="只按本次明确的水彩短身设计",
                      references=[{"path": str(ref), "role": "style", "use_for": "只参考轮廓"}])
        request = self.read("imagegen-request.json")
        self.assertEqual(self.read("job.json")["style_source"], "explicit_text")
        self.assertIn(str(ref), request["referenced_image_paths"])
        self.assertNotIn(str(self.builtin_image), request["referenced_image_paths"])
        self.assertIn("以此要求为准", request["prompt"])
        self.assertNotIn("通用默认画风：", request["prompt"])

    def test_identity_layout_and_overall_references_do_not_replace_builtin_style(self):
        ref = self.base / "selected.png"
        make_png(ref, width=7)
        for role in ["identity", "layout", "overall"]:
            with self.subTest(role=role):
                self.output = self.base / role
                self.planning(output_dir=str(self.output), references=[{
                    "path": str(ref), "role": role, "use_for": "只采用身份、布局或背景范围，不提供角色画风"}])
                job = self.read("job.json")
                self.assertEqual(job["style_source"], "builtin_reference")
                self.assertEqual([r["role"] for r in job["references"]], [role, "style"])
                self.assertIn(str(self.builtin_image), self.read("imagegen-request.json")["referenced_image_paths"])

    def test_disabling_builtin_needs_no_asset_and_still_supplies_text_default(self):
        self.metadata_path.unlink()
        self.planning(use_builtin_style=False)
        request, job = self.read("imagegen-request.json"), self.read("job.json")
        self.assertEqual(job["style_source"], "text_default")
        self.assertEqual(job["references"], [])
        self.assertEqual(request["referenced_image_paths"], [str(self.source)])
        self.assertIn("通用默认画风：", request["prompt"])
        self.assertIn("二维彩色Q版", request["prompt"])
        self.assertNotIn("Lulu", request["prompt"])

    def test_missing_builtin_metadata_fails_before_creating_output(self):
        self.metadata_path.unlink()
        with self.assertRaisesRegex(ValueError, "metadata missing"):
            self.planning()
        self.assertFalse(self.output.exists())

    def test_missing_builtin_image_fails_before_creating_output(self):
        self.builtin_image.unlink()
        with self.assertRaisesRegex(ValueError, "image missing"):
            self.planning()
        self.assertFalse(self.output.exists())

    def test_tampered_builtin_image_is_not_silently_used(self):
        make_png(self.builtin_image, width=19)
        with self.assertRaisesRegex(ValueError, "SHA-256 mismatch"):
            self.planning()
        self.assertFalse(self.output.exists())

    def test_builtin_metadata_cannot_reference_absolute_or_escaped_image_paths(self):
        outside = self.base / "outside.png"
        make_png(outside, width=8)
        for image_name in [str(self.builtin_image), "../outside.png"]:
            with self.subTest(path=image_name):
                self.metadata_path.write_text(json.dumps({**self.metadata, "image": image_name,
                                                          "sha256": ops.digest(outside)}), encoding="utf-8")
                with self.assertRaisesRegex(ValueError, "inside assets|outside assets"):
                    self.planning()
        self.assertFalse(self.output.exists())

    def test_builtin_default_keeps_existing_waiting_gates(self):
        choices = [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}]
        cases = [("permission", {"scenario": "small_person"}, "recommendation_needed"),
                 ("review", {"inputs_reviewed": False}, "needs_input_review"),
                 ("choice", {"style_selection": "needed", "style_options": choices}, "style_choice_needed")]
        for name, changes, expected in cases:
            with self.subTest(gate=name):
                self.output = self.base / name
                self.planning(output_dir=str(self.output), **changes)
                job = self.read("job.json")
                self.assertEqual(job["status"], expected)
                self.assertEqual(job["style_source"], "builtin_reference")
                self.assertFalse((self.output / "imagegen-request.json").exists())
                self.assertEqual(job["options"]["style_selection"], changes.get("style_selection", "resolved"))
                self.assertEqual(job["references"][0]["sha256"], ops.digest(self.builtin_image))

    def test_collect_verifies_builtin_reference_unchanged_like_other_inputs(self):
        self.planning()
        result = self.generated()
        make_png(self.builtin_image, width=17)
        with self.assertRaisesRegex(ValueError, "changed or missing"):
            ops.collect(self.output / "job.json", result)
        self.assertFalse((self.output / "final.png").exists())

    def test_pet_object_defaults_to_scene_and_keeps_people(self):
        self.planning(scenario="pet_object")
        self.assertEqual(self.read("job.json")["options"]["placement"], "in_scene")
        prompt = self.read("imagegen-request.json")["prompt"]
        self.assertIn("原有真人全部保留", prompt)
        self.assertIn("保留照片中的真实宠物/物件", prompt)
        self.assertIn("按subject_details清单新增、复用或修改", prompt)
        self.assertNotIn("将指定宠物/物件画成对应Q版", prompt)
        self.assertIn("接触阴影", prompt)

    def test_existing_pet_interaction_character_is_reused_without_duplicate(self):
        self.planning(scenario="pet_object", scene_intent="复用已有Q版，只改摸猫互动。",
                      subject_details="原图本身已有选定小人；复用已有Q版只改互动，不新增角色。")
        prompt = self.read("imagegen-request.json")["prompt"]
        self.assertIn("复用已有Q版只改互动，不新增角色", prompt)
        self.assertIn("已有本次选定Q版角色且只要求修改时，复用并只改指定部分，不另添一份", prompt)
        self.assertIn("只有用户要求且原图没有该角色时才新增", prompt)
        self.assertIn("原图已有选定角色且仅改互动时不再增加一份", prompt)
        self.assertIn("保留照片中的真实宠物/物件", prompt)
        self.assertNotIn("默认新增人类Q版", prompt)

    def test_compact_default_is_conditional_and_approved_reference_has_priority(self):
        ref = self.base / "approved.png"
        make_png(ref, width=9)
        self.planning(references=[{"path": "approved.png", "role": "style", "use_for": "已认可短身比例，只改动作"}])
        request = self.read("imagegen-request.json")
        prompt = request["prompt"]
        self.assertIn(str(ref), request["referenced_image_paths"])
        self.assertIn("明确认可的角色资产或比例参考优先", prompt)
        self.assertIn("不叠加通用默认的二维画法或头身目标", prompt)
        self.assertNotIn("新设计且没有特定认可资产时，以约两头身为起点", prompt)
        self.assertNotIn("通用默认画风：", prompt)
        self.assertIn("不为填满原真人身高", prompt)
        self.assertIn("调整角色整体尺度使其合理入景", prompt)
        self.assertIn("仍需目视检查", prompt)

    def test_explicit_pet_chibi_design_does_not_authorize_removing_real_pet(self):
        self.planning(scenario="pet_object", scene_intent="猫咪旁加入同款宠物Q版。",
                      subject_details="用户明确只要宠物本身的Q版设计，保留真实猫咪。")
        prompt = self.read("imagegen-request.json")["prompt"]
        self.assertIn("用户明确只要宠物本身的Q版设计", prompt)
        self.assertIn("只有subject_details明确要求宠物/物件本身的Q版设计时", prompt)
        self.assertIn("不默认删除、替换或动漫化原来的真实宠物/物件", prompt)

    def test_no_person_supports_both_placements(self):
        for index, placement in enumerate(["corner", "in_scene"]):
            with self.subTest(placement=placement):
                self.output = self.base / f"run{index}"
                self.planning(scenario="no_person", placement=placement, output_dir=str(self.output))
                self.assertEqual(self.read("job.json")["options"]["placement"], placement)
                self.assertIn("场景 no_person", self.read("imagegen-request.json")["prompt"])

    def test_no_person_preserves_incidental_people_without_false_classification(self):
        self.planning(scenario="no_person", scene_intent="街边茶壶旁加入Q版人物。",
                      subject_details="Agent已看图，背景有路人与边缘手臂，没有需要处理的主要真人。")
        prompt = self.read("imagegen-request.json")["prompt"]
        self.assertIn("按Agent审图判断", prompt)
        self.assertIn("背景路人、边缘手臂等非主要人物照常保留", prompt)
        self.assertIn("不因它们出现就阻塞本路由或自动删人", prompt)
        self.assertIn("standard或small_person", prompt)
        self.assertNotIn("若实际原图含真人，停止删人", prompt)

    def test_small_person_without_replacement_permission_has_no_request(self):
        report = self.planning(scenario="small_person")
        self.assertEqual(report["status"], "recommendation_needed")
        self.assertIsNone(report["request"])
        self.assertFalse((self.output / "imagegen-request.json").exists())
        self.assertFalse((self.output / "prompt.txt").exists())
        with self.assertRaisesRegex(ValueError, "executable"):
            ops.collect(self.output / "job.json", self.source)

    def test_small_person_with_explicit_permission_creates_request(self):
        self.planning(scenario="small_person", replace_real_person=True)
        self.assertIn("用户已明确批准", self.read("imagegen-request.json")["prompt"])
        self.assertIn("只移除subject_details指定", self.read("imagegen-request.json")["prompt"])

    def test_other_routes_cannot_delete_real_people(self):
        for scenario in ["standard", "no_person", "pet_object"]:
            with self.subTest(scenario=scenario), self.assertRaisesRegex(ValueError, "only supported"):
                self.planning(scenario=scenario, replace_real_person=True)
        self.assertFalse(self.output.exists())

    def test_unreviewed_inputs_cannot_create_executable_request(self):
        report = self.planning(inputs_reviewed=False)
        self.assertEqual(report["status"], "needs_input_review")
        self.assertFalse((self.output / "imagegen-request.json").exists())

    def test_style_needed_waits_with_selection_schema_and_no_request(self):
        choices = [{"id": "soft", "label": "柔和短身", "description": "用已展示的柔和插画参考"},
                   {"id": "line", "label": "清爽线稿"}]
        report = self.planning(scenario="no_person", placement="in_scene", style_selection="needed",
                               style_options=choices, background_render_style="soft_illustrated")
        job, picker = self.read("job.json"), self.read("style-picker.json")
        self.assertEqual(report["status"], "style_choice_needed")
        self.assertIsNone(report["request"])
        self.assertFalse((self.output / "imagegen-request.json").exists())
        self.assertFalse((self.output / "prompt.txt").exists())
        self.assertEqual(set(picker), {"questions"})
        self.assertEqual(len(picker["questions"]), 1)
        question = picker["questions"][0]
        self.assertEqual(set(question), {"title", "options"})
        self.assertTrue(question["title"].startswith("这张照片想用哪种Q版画风？"))
        self.assertEqual(question["options"], ["柔和短身：用已展示的柔和插画参考", "清爽线稿"])
        self.assertEqual(job["options"]["scenario"], "no_person")
        self.assertEqual(job["options"]["placement"], "in_scene")
        self.assertEqual(job["options"]["background_render_style"], "soft_illustrated")
        self.assertFalse(job["options"]["replace_real_person"])
        self.assertIn("actual available candidate reference images", job["next_action"])
        self.assertIn("never select the first option or proceed on timeout", job["next_action"])
        self.assertIn("ordinary text", job["next_action"])
        with self.assertRaisesRegex(ValueError, "executable"):
            ops.collect(self.output / "job.json", self.source)

    def test_style_needed_requires_two_or_three_distinct_nonempty_options(self):
        bad_options = [[], [{"id": "a", "label": "A"}],
                       [{"id": str(i), "label": str(i)} for i in range(4)],
                       [{"id": "same", "label": "A"}, {"id": "same", "label": "B"}],
                       [{"id": "a", "label": "Same"}, {"id": "b", "label": " same "}],
                       [{"id": " ", "label": "A"}, {"id": "b", "label": "B"}],
                       [{"id": "a", "label": ""}, {"id": "b", "label": "B"}]]
        for choices in bad_options:
            with self.subTest(choices=choices), self.assertRaises(ValueError):
                self.planning(style_selection="needed", style_options=choices)
        self.assertFalse(self.output.exists())

    def test_resolved_and_delegated_styles_do_not_repeat_selection(self):
        for selection in ["resolved", "delegate"]:
            with self.subTest(selection=selection):
                self.output = self.base / selection
                report = self.planning(style_selection=selection, output_dir=str(self.output))
                self.assertEqual(report["status"], "planned")
                self.assertTrue((self.output / "imagegen-request.json").is_file())
                self.assertFalse((self.output / "style-picker.json").exists())
                self.assertEqual(self.read("job.json")["options"]["style_selection"], selection)

    def test_style_choice_never_bypasses_replacement_or_input_review_gates(self):
        choices = [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}]
        for name, changes, expected in [
            ("permission", {"scenario": "small_person"}, "recommendation_needed"),
            ("review", {"inputs_reviewed": False}, "needs_input_review"),
        ]:
            with self.subTest(gate=name):
                self.output = self.base / name
                report = self.planning(style_selection="needed", style_options=choices,
                                       output_dir=str(self.output), **changes)
                self.assertEqual(report["status"], expected)
                self.assertFalse((self.output / "imagegen-request.json").exists())
                self.assertFalse((self.output / "style-picker.json").exists())

    def test_answered_style_uses_new_plan_and_keeps_waiting_job_unchanged(self):
        choices = [{"id": "a", "label": "A"}, {"id": "b", "label": "B"}]
        self.planning(style_selection="needed", style_options=choices)
        original_job = self.output / "job.json"
        before = original_job.read_bytes()
        ref = self.base / "chosen-style.png"
        make_png(ref, width=11)
        self.output = self.base / "answered"
        self.planning(style_selection="resolved", output_dir=str(self.output),
                      references=[{"path": str(ref), "role": "style", "use_for": "用户选中B的短身画风"}])
        self.assertEqual(self.read("job.json")["status"], "planned")
        self.assertIn(str(ref), self.read("imagegen-request.json")["referenced_image_paths"])
        self.assertEqual(original_job.read_bytes(), before)

    def test_missing_review_flag_defaults_to_false(self):
        del self.config["inputs_reviewed"]
        self.assertEqual(self.planning()["status"], "needs_input_review")

    def test_boolean_strings_are_not_authorization(self):
        for name in ["replace_real_person", "inputs_reviewed", "add_text", "use_builtin_style"]:
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, "true or false"):
                self.planning(**{name: "true"})
        self.assertFalse(self.output.exists())

    def test_soft_background_and_decoration_keep_text_independent(self):
        self.planning(background_render_style="soft_illustrated", decoration="full_journal")
        prompt = self.read("imagegen-request.json")["prompt"]
        self.assertIn("柔和插画化", prompt)
        self.assertIn("full_journal", prompt)
        self.assertIn("add_text=false", prompt)

    def test_text_requires_explicit_switch_and_uses_actual_content(self):
        with self.assertRaisesRegex(ValueError, "add_text=true"):
            self.planning(text="Just me")
        self.planning(add_text=True, text="Just me")
        prompt = self.read("imagegen-request.json")["prompt"]
        self.assertIn('"Just me"', prompt)
        self.assertNotIn("add_text=false", prompt)

    def test_relative_config_asset_and_output_paths(self):
        directory = self.base / "configs"
        directory.mkdir()
        self.spec_path = directory / "spec.json"
        self.planning(source_photo="../source.png", output_dir="../run")
        job = self.read("job.json")
        self.assertEqual(job["source"]["path"], str(self.source.resolve()))
        self.assertEqual(job["output_dir"], str(self.output.resolve()))

    def test_role_references_are_passed_and_hashed(self):
        ref = self.base / "style.png"
        make_png(ref, width=8)
        self.planning(references=[{"path": "style.png", "role": "style", "use_for": "只锁短身线条"}])
        job, request = self.read("job.json"), self.read("imagegen-request.json")
        self.assertEqual(job["references"][0]["sha256"], ops.digest(ref))
        self.assertEqual(request["referenced_image_paths"], [str(self.source), str(ref)])
        self.assertIn("图2参考角色=style", request["prompt"])
        self.assertIn("只锁短身线条", request["prompt"])

    def test_explicit_profile_resolves_its_own_relative_paths(self):
        folder = self.base / "private-profile"
        folder.mkdir()
        ref = folder / "identity.png"
        make_png(ref, width=7)
        profile = folder / "profile.json"
        profile.write_text(json.dumps({"references": [{"id": "self", "path": "identity.png", "role": "identity", "use_for": "本人识别特征"}]}), encoding="utf-8")
        self.spec_path.write_text(json.dumps({**self.config, "reference_ids": ["self"]}), encoding="utf-8")
        ops.plan(self.spec_path, profile)
        self.assertEqual(self.read("job.json")["references"][0]["path"], str(ref))
        self.assertIn("图2参考角色=identity", self.read("imagegen-request.json")["prompt"])

    def test_profile_is_never_silently_selected(self):
        with self.assertRaisesRegex(ValueError, "explicit --profile"):
            self.planning(reference_ids=["self"])
        self.assertFalse(self.output.exists())

    def test_missing_reference_rejected_before_any_output(self):
        with self.assertRaisesRegex(ValueError, "existing file"):
            self.planning(references=[{"path": "missing.png", "role": "style", "use_for": "画风"}])
        self.assertFalse(self.output.exists())

    def test_plan_never_overwrites_source_reference_or_existing_output(self):
        before = self.source.read_bytes()
        with self.assertRaisesRegex(ValueError, "never overwrite"):
            self.planning(output_dir="source.png")
        self.planning()
        first = (self.output / "job.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "never overwrite"):
            self.planning()
        self.assertEqual((self.output / "job.json").read_bytes(), first)
        self.assertEqual(self.source.read_bytes(), before)

    def test_strict_subject_plans_only_transparent_asset(self):
        self.planning(edit_scope="strict_subject")
        request = self.read("imagegen-request.json")
        self.assertTrue(request["transparent_background"])
        self.assertIn("只生成一组独立Q版透明PNG资产", request["prompt"])
        self.assertIn("不能声称已完成严格保脸", request["prompt"])
        self.assertIn("描边样式、颜色及粗细服从已认可参考或本次指定", request["prompt"])
        self.assertIn("不强制厚白边", request["prompt"])
        self.assertNotIn("场景 standard：真实照片为主", request["prompt"])

    def test_strict_subject_other_routes_not_misrepresented(self):
        with self.assertRaisesRegex(ValueError, "standard only"):
            self.planning(scenario="pet_object", edit_scope="strict_subject")

    def test_collect_copies_new_png_and_keeps_user_and_visual_pending(self):
        self.planning()
        result = self.generated()
        source_before = self.source.read_bytes()
        report = ops.collect(self.output / "job.json", result)
        self.assertEqual((self.output / "final.png").read_bytes(), result.read_bytes())
        self.assertEqual(self.source.read_bytes(), source_before)
        self.assertEqual(report["status"], "ready_for_user_review")
        job, qa = self.read("job.json"), self.read("qa.json")
        self.assertEqual(job["user_acceptance"], "pending")
        self.assertEqual(qa["visual_review"]["status"], "pending")
        self.assertEqual(qa["technical_checks"]["png_structure"]["width"], 4)
        self.assertFalse(qa["technical_checks"]["png_structure"]["pixel_decode_checked"])
        self.assertFalse(qa["technical_checks"]["strict_subject_preservation_verified"])
        self.assertEqual(job["generation"]["result_sha256"], ops.digest(result))

    def test_collect_review_is_copied_exactly_without_upgrading_acceptance(self):
        self.planning()
        result, review = self.generated(), self.base / "actual-review.json"
        contents = '{"checked_by":"Agent","visual_checks":{"pose":"needs_revision"},"user_acceptance":"accepted"}\n'
        review.write_text(contents, encoding="utf-8")
        ops.collect(self.output / "job.json", result, review)
        self.assertEqual((self.output / "visual-review.json").read_text(encoding="utf-8"), contents)
        qa = self.read("qa.json")
        self.assertEqual(qa["visual_review"]["report"]["visual_checks"]["pose"], "needs_revision")
        self.assertEqual(qa["user_acceptance"], "pending")
        self.assertEqual(self.read("job.json")["user_acceptance"], "pending")

    def test_collect_refuses_changed_source(self):
        self.planning()
        result = self.generated()
        make_png(self.source, width=19)
        with self.assertRaisesRegex(ValueError, "changed or missing"):
            ops.collect(self.output / "job.json", result)
        self.assertFalse((self.output / "final.png").exists())

    def test_collect_refuses_changed_reference(self):
        ref = self.base / "ref.png"
        make_png(ref, width=8)
        self.planning(references=[{"path": "ref.png", "role": "overall", "use_for": "整体风格"}])
        result = self.generated()
        make_png(ref, width=9)
        with self.assertRaisesRegex(ValueError, "changed or missing"):
            ops.collect(self.output / "job.json", result)

    def test_source_and_copied_source_cannot_fake_generated_result(self):
        self.planning()
        with self.assertRaisesRegex(ValueError, "source/reference as"):
            ops.collect(self.output / "job.json", self.source)
        copied = self.generated()
        copied.write_bytes(self.source.read_bytes())
        with self.assertRaisesRegex(ValueError, "unchanged copy"):
            ops.collect(self.output / "job.json", copied)

    def test_old_result_is_not_collected(self):
        self.planning()
        result = self.generated()
        stamp = self.read("job.json")["created_at_ns"] - 10 ** 9
        os.utime(result, ns=(stamp, stamp))
        with self.assertRaisesRegex(ValueError, "predates"):
            ops.collect(self.output / "job.json", result)

    def test_collect_refuses_existing_final_and_second_collect(self):
        self.planning()
        result = self.generated()
        final = self.output / "final.png"
        final.write_bytes(b"existing output")
        with self.assertRaisesRegex(ValueError, "overwrite"):
            ops.collect(self.output / "job.json", result)
        self.assertEqual(final.read_bytes(), b"existing output")
        final.unlink()
        ops.collect(self.output / "job.json", result)
        with self.assertRaisesRegex(ValueError, "uncollected"):
            ops.collect(self.output / "job.json", result)

    def test_strict_collect_is_asset_not_final_or_face_lock_completion(self):
        self.planning(edit_scope="strict_subject")
        ops.collect(self.output / "job.json", self.generated())
        job = self.read("job.json")
        self.assertTrue((self.output / "chibi.png").is_file())
        self.assertFalse((self.output / "final.png").exists())
        self.assertTrue(job["delivery"]["composition_required"])
        self.assertIsNone(job["delivery"]["final_image"])
        self.assertFalse(job["delivery"]["strict_subject_preservation_verified"])
        self.assertEqual(job["delivery"]["stage"], "asset_ready_needs_composition")

    def test_strict_collect_rejects_nonalpha_png(self):
        self.planning(edit_scope="strict_subject")
        with self.assertRaisesRegex(ValueError, "alpha/tRNS"):
            ops.collect(self.output / "job.json", self.generated(alpha=False))

    def test_corrupt_crc_and_non_png_rejected_without_output(self):
        self.planning()
        result = self.generated()
        result.write_bytes(b"not a png")
        with self.assertRaisesRegex(ValueError, "not a PNG"):
            ops.collect(self.output / "job.json", result)
        result = self.generated()
        data = bytearray(result.read_bytes())
        data[20] ^= 1
        result.write_bytes(data)
        with self.assertRaisesRegex(ValueError, "CRC"):
            ops.collect(self.output / "job.json", result)
        self.assertFalse((self.output / "final.png").exists())

    def test_doctor_and_plan_cli_need_no_external_service(self):
        doctor = subprocess.run([sys.executable, str(SCRIPT), "doctor"], capture_output=True, text=True)
        self.assertEqual(doctor.returncode, 0, doctor.stderr)
        report = json.loads(doctor.stdout)
        self.assertTrue(report["stdlib_only"])
        self.assertFalse(report["network_calls"])
        self.spec_path.write_text(json.dumps({**self.config, "use_builtin_style": False}), encoding="utf-8")
        report = subprocess.run([sys.executable, str(SCRIPT), "plan", "--config", "job-spec.json"], cwd=self.base, capture_output=True, text=True)
        self.assertEqual(report.returncode, 0, report.stderr)
        self.assertEqual(json.loads(report.stdout)["status"], "planned")


if __name__ == "__main__":
    unittest.main()
