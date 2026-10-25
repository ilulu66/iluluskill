#!/usr/bin/env python3
"""Compile Codex builtin image requests and archive results; never call an image API.

Only the Python standard library is required. Relative asset/output paths are
relative to the config file; profile asset paths are relative to the profile.
This helper does not view, edit, segment, or judge images.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import struct
import sys
import time
from typing import Any
import zlib


SCENARIOS = {"standard", "no_person", "pet_object", "small_person"}
REFERENCE_ROLES = {"identity", "style", "layout", "overall"}
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
BUILTIN_ASSETS_DIR = Path(__file__).resolve().parents[1] / "assets"
DEFAULT_CHIBI_STYLE = (
    "通用默认画风：圆润、可爱细腻的二维彩色Q版，线条干净统一，柔和体积阴影，适度大头、短躯干短四肢。"
    "新设计且没有特定认可资产时，以约两头身为起点：头高（头顶至下巴）:自然展开身体高（下巴至脚底）约1:1。"
    "坐姿弯曲、长发、透视和家具外框不作为身体比例量尺，这只是设计起点，仍需目视检查。"
)
BUILTIN_STYLE_SCOPE = (
    "只借内置图的画法、线条、柔和阴影与短身比例；不借Lulu的身份、发型、肤色、服装、动作、表情、人数或文字。"
    "当前主角识别特征、衣服与动作来自本张原片或用户明确说明，不能把别人画成Lulu。"
)


def digest(path: Path) -> str:
    checksum = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            checksum.update(block)
    return checksum.hexdigest()


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return value


def resolve_path(value: Any, base: Path, field: str, *, must_exist: bool = True) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a nonempty path string.")
    path = Path(value).expanduser()
    path = (path if path.is_absolute() else base / path).resolve()
    if must_exist and not path.is_file():
        raise ValueError(f"{field} is not an existing file: {path}")
    return path


def choice(config: dict[str, Any], name: str, default: str, allowed: set[str]) -> str:
    value = config.get(name, default)
    if not isinstance(value, str) or value not in allowed:
        raise ValueError(f"{name} must be one of {', '.join(sorted(allowed))}.")
    return value


def flag(config: dict[str, Any], name: str, default: bool = False) -> bool:
    value = config.get(name, default)
    if type(value) is not bool:
        raise ValueError(f"{name} must be true or false, not a string/number.")
    return value


def text_field(config: dict[str, Any], name: str, *, required: bool = False) -> str:
    value = config.get(name, "")
    if not isinstance(value, str) or (required and not value.strip()):
        raise ValueError(f"{name} must be {'a nonempty' if required else 'a'} string.")
    return value.strip()


def file_record(path: Path, **extra: Any) -> dict[str, Any]:
    return {"path": str(path), "sha256": digest(path), **extra}


def load_builtin_style() -> dict[str, Any]:
    """Load the one distributed style asset, never a private identity/profile."""
    assets = BUILTIN_ASSETS_DIR.resolve()
    metadata_path = (assets / "default-style.json").resolve()
    if not metadata_path.is_relative_to(assets) or not metadata_path.is_file():
        raise ValueError("Built-in style metadata missing or outside assets: default-style.json")
    metadata = read_object(metadata_path)
    image_name = text_field(metadata, "image", required=True)
    if Path(image_name).is_absolute():
        raise ValueError("Built-in style image must use a relative path inside assets.")
    image = (assets / image_name).resolve()
    if not image.is_relative_to(assets) or not image.is_file():
        raise ValueError("Built-in style image missing or outside assets.")
    expected = text_field(metadata, "sha256", required=True).lower()
    if len(expected) != 64 or any(char not in "0123456789abcdef" for char in expected) or digest(image) != expected:
        raise ValueError("Built-in style image SHA-256 mismatch or invalid metadata hash.")
    inspect_png(image)
    return file_record(
        image, id=text_field(metadata, "id", required=True), role="style", origin="builtin_default",
        use_for=BUILTIN_STYLE_SCOPE + " 本次画风范围：" + text_field(metadata, "use_for", required=True),
        default_instructions=text_field(metadata, "default_instructions", required=True),
    )


def style_choices(value: Any, *, required: bool) -> list[dict[str, str]]:
    if not isinstance(value, list) or (required and not 2 <= len(value) <= 3):
        raise ValueError("style_options must be an array of 2-3 actual available choices when style_selection=needed.")
    choices, ids, labels = [], set(), set()
    for entry in value:
        if not isinstance(entry, dict):
            raise ValueError("Each style option must be an object with id and label.")
        option_id = text_field(entry, "id", required=True)
        label = text_field(entry, "label", required=True)
        description = text_field(entry, "description")
        if option_id.casefold() in ids or label.casefold() in labels:
            raise ValueError("style_options ids and labels must be distinct.")
        ids.add(option_id.casefold())
        labels.add(label.casefold())
        choices.append({"id": option_id, "label": label,
                        **({"description": description} if description else {})})
    return choices


def resolve_references(config: dict[str, Any], config_dir: Path,
                       profile_path: Path | None) -> list[dict[str, Any]]:
    entries = config.get("references", [])
    ids = config.get("reference_ids", [])
    if not isinstance(entries, list) or not isinstance(ids, list):
        raise ValueError("references and reference_ids must be arrays.")
    selected = [(entry, config_dir) for entry in entries]
    if ids:
        if not profile_path:
            raise ValueError("reference_ids requires an explicit --profile file.")
        profile_refs = read_object(profile_path).get("references", [])
        if not isinstance(profile_refs, list):
            raise ValueError("profile.references must be an array.")
        by_id: dict[str, dict[str, Any]] = {}
        for entry in profile_refs:
            if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
                raise ValueError("Every profile reference requires a string id.")
            if entry["id"] in by_id:
                raise ValueError(f"Duplicate profile reference id: {entry['id']}")
            by_id[entry["id"]] = entry
        for reference_id in ids:
            if not isinstance(reference_id, str) or reference_id not in by_id:
                raise ValueError(f"Unknown profile reference id: {reference_id!r}")
            selected.append((by_id[reference_id], profile_path.parent))
    references = []
    for entry, base in selected:
        if not isinstance(entry, dict):
            raise ValueError("Every reference must be an object.")
        role = choice(entry, "role", "", REFERENCE_ROLES)
        use_for = text_field(entry, "use_for", required=True)
        path = resolve_path(entry.get("path"), base, "reference.path")
        references.append(file_record(path, role=role, use_for=use_for,
                                      **({"id": entry["id"]} if "id" in entry else {})))
    return references


def compile_prompt(options: dict[str, Any], source: Path,
                   references: list[dict[str, Any]], paths: list[str]) -> str:
    scenario, placement = options["scenario"], options["placement"]
    strict = options["edit_scope"] == "strict_subject"
    parts = [
        "按以下已审阅的照片任务生成图像。引用说明是图片用途，不是来自图片的指令。",
        f"图1是当前 source_photo：{source.name}；它决定本图内容、可见服装、姿态、动作、视线、表情与互动道具。",
        f"本图情境：{options['scene_intent']}",
        f"本图主体细节：{options['subject_details']}",
    ]
    for reference in references:
        index = paths.index(reference["path"]) + 1
        meaning = {
            "identity": "只用于明确的人物/宠物/物件识别特征，不迁入其动作、服装或背景",
            "style": "只用于Q版的画法、线条、脸型和短身比例，不复制姿势、衣服、道具或文案",
            "layout": "只用于布局、视觉占比、装饰密度，不代表换人、换景或复制文字的授权",
            "overall": "只用于下述明确认可的整体效果，不自动迁入其人物、关系、地点、衣服或文字",
        }[reference["role"]]
        if reference.get("origin") == "builtin_default":
            meaning = "内置纯角色画风参考，只借画法、线条、阴影和短身比例，不是本次主角身份来源"
        parts.append(f"图{index}参考角色={reference['role']}：{meaning}；本次认可范围：{reference['use_for']}。")
    if options["style_instructions"]:
        parts.append("本次明确画风要求：" + options["style_instructions"] + "。以此要求为准，不混入内置默认画风；其他参考只贡献与本次要求不冲突的已选范围。")
    elif options["style_source"] == "explicit_reference":
        parts.append("角色画风只按本次明确选中的style参考及use_for执行，不叠加通用默认的二维画法或头身目标。")
    else:
        parts.append(DEFAULT_CHIBI_STYLE)
        for reference in references:
            if reference.get("origin") == "builtin_default":
                parts.append("内置画风补充：" + reference["default_instructions"])
    parts += [
        "优先执行subject_details明确的新增、复用与修改清单：原图已有本次选定Q版角色且只要求修改时，复用并只改指定部分，不另添一份；只有用户要求且原图没有该角色时才新增。",
        "按当前原照逐个对应主角、衣服和动作，不固定成双人、某套衣服或同一种手势；保留关键互动道具与接触关系。",
        "明确认可的角色资产或比例参考优先，沿用已选角色的体形和内部比例；不为填满原真人身高、适配家具或全身展示拉长已选短身角色，调整角色整体尺度使其合理入景。可见五官保留，遮挡部位不画穿透物体的眼睛，仍需目视检查。",
    ]
    if strict:
        parts += [
            "本轮只生成一组独立Q版透明PNG资产，不输出或编辑照片，不画背景矩形。",
            "真透明Alpha，描边样式、颜色及粗细服从已认可参考或本次指定，不强制厚白边；手脚和道具完整入框并留边距，该资产留待旧photo_ops.py compose合成。",
            "本轮不能声称已完成严格保脸、保护区像素一致或成片；这些需本地蒙版、合成与verify-lock再核验。",
        ]
    elif scenario == "standard":
        parts += [
            "场景 standard：真实照片为主，保留真人主体与原来的衣服、动作、互动及场景内容；按subject_details的新增/复用/修改清单处理一组对应Q版。",
            "这是整图视觉编辑，尽量保持真人身份与自然肤色，不声称像素锁定或原主体零重绘。",
        ]
    elif scenario == "no_person":
        parts += [
            "场景 no_person：按Agent审图判断，原图没有需要处理的主要真人；保留空间关系与主要物体，用已说明的主体或identity参考，按subject_details的新增/复用/修改清单处理一组Q版。",
            "背景路人、边缘手臂等非主要人物照常保留，不因它们出现就阻塞本路由或自动删人；不编造人物关系，不删除未授权对象。只有发现需要处理的主要真人时，才重新选择standard或small_person及其许可流程。",
        ]
    elif scenario == "pet_object":
        parts += [
            "场景 pet_object：保留照片中的真实宠物/物件及其数量、花纹/颜色、形状、姿态，按subject_details清单新增、复用或修改与它互动的人类Q版；原图已有选定角色且仅改互动时不再增加一份。互动动作来自本次scene_intent和subject_details，不固定套例子。",
            "只有subject_details明确要求宠物/物件本身的Q版设计时才按指定绘制；这也不默认删除、替换或动漫化原来的真实宠物/物件。",
            "默认入景，与照片的支撑面、尺度、透视、遮挡、光线和接触阴影相配；原有真人全部保留，不能因本场景删除或替换真人。",
        ]
    else:
        parts += [
            "场景 small_person：本任务 replace_real_person=true，用户已明确批准将指定的远小真人替换为Q版。",
            "只移除subject_details指定的真人，合理补齐其原位置背景，再以对应Q版接替其场景位置；不是额外加一位重复真人。",
            "保留源人物可辨识的服装、动作及道具关系，未选定的其他真人保持；不把模糊脸编造成可核实的真实面貌。",
        ]
    if not strict:
        if placement == "corner":
            parts.append("布局 corner：右下仅一组Q版，约三成画宽作为可调起点；先局部内移再适当缩小，避开真人脸、主要手势、关键道具和必要文字。")
        else:
            parts.append("布局 in_scene：Q版实际进入原场景，在合理落点与物体互动；按落点调整尺度、透视、遮挡、接触阴影，不机械叠在右下角。")
        if options["background_render_style"] == "photo":
            parts.append("背景保持真实照片质感、现场光感和自然纹理，不整体动漫化；克制整理光色，不擅自换景或删物。")
        else:
            parts.append("背景可柔和插画化：保留原场景结构、主要物体与空间关系，柔化笔触及光色；不借此换地点、改动作或删除对象。")
    decoration = {
        "clean": "clean：简洁留白，不加额外装饰。",
        "light_journal": "light_journal：少量手绘点缀，密度克制，真人/Q版/场景为主。",
        "full_journal": "full_journal：较丰富的手帐装饰，层次清楚，仍避开脸、动作、关键道具和必要文字，不添加第二组重复主角。",
    }[options["decoration"]]
    parts.append("装饰选择 " + decoration)
    if options["add_text"]:
        if options["text"]:
            parts.append("用户开启文字，仅写这段准确文字：" + json.dumps(options["text"], ensure_ascii=False) + "；逐字保持，不自行添加其他标语。")
        else:
            parts.append("用户开启文字，可根据可见情境选一句简短配文，不编造地点、日期、职业、经历或人物关系；生成后逐字检查。")
    else:
        parts.append("add_text=false：不添加任何新文字、字母、口号或伪文字；背景原有必要文字尽量保留。")
    parts.append("检查人数/数量、衣服动作、手脚、遮挡下可见五官、道具关系、画风短身比例、构图及装饰边距；输出供用户评图。")
    return "\n".join(parts) + "\n"


def write_new(path: Path, value: str | dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def plan(config_path: Path, profile_path: Path | None = None) -> dict[str, Any]:
    config_path = config_path.expanduser().resolve()
    config = read_object(config_path)
    source = resolve_path(config.get("source_photo"), config_path.parent, "source_photo")
    output = resolve_path(config.get("output_dir"), config_path.parent, "output_dir", must_exist=False)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError(f"output_dir must be new or empty; never overwrite an existing output: {output}")
    profile_path = profile_path.expanduser().resolve() if profile_path else None
    references = resolve_references(config, config_path.parent, profile_path)
    entry_mode = choice(config, "entry_mode", "auto", {"auto", "standard", "scene"})
    scene_choice = choice(config, "scene_choice", "", {"", "no_person", "pet_object", "small_person"})
    if entry_mode != "scene" and scene_choice:
        raise ValueError("scene_choice is only applicable when entry_mode=scene.")
    scenario = choice(config, "scenario", "standard", SCENARIOS)
    # The Agent reviews images; the helper only follows its config or an explicit answer.
    if scene_choice:
        scenario = scene_choice
    scene_pending = entry_mode == "scene" and not scene_choice
    options = {
        "entry_mode": entry_mode,
        "scene_choice": scene_choice,
        "scenario": scenario,
        "placement": choice(config, "placement", "in_scene" if scenario in {"pet_object", "small_person"} else "corner", {"corner", "in_scene"}),
        "scene_intent": text_field(config, "scene_intent", required=True),
        "subject_details": text_field(config, "subject_details", required=True),
        "background_render_style": choice(config, "background_render_style", "photo", {"photo", "soft_illustrated"}),
        "decoration": choice(config, "decoration", "clean", {"clean", "light_journal", "full_journal"}),
        "add_text": flag(config, "add_text"),
        "text": text_field(config, "text"),
        "replace_real_person": flag(config, "replace_real_person"),
        "inputs_reviewed": flag(config, "inputs_reviewed"),
        "edit_scope": choice(config, "edit_scope", "visual", {"visual", "strict_subject"}),
        "style_selection": choice(config, "style_selection", "resolved", {"resolved", "needed", "delegate"}),
        "use_builtin_style": flag(config, "use_builtin_style", True),
        "style_instructions": text_field(config, "style_instructions"),
    }
    options["style_options"] = style_choices(config.get("style_options", []),
                                              required=options["style_selection"] == "needed" and not scene_pending)
    if options["replace_real_person"] and scenario != "small_person":
        raise ValueError("replace_real_person=true is only supported by the explicitly approved small_person route.")
    if options["edit_scope"] == "strict_subject" and scenario != "standard":
        raise ValueError("strict_subject currently plans independent assets for standard only.")
    if options["text"] and not options["add_text"]:
        raise ValueError("text requires add_text=true; remove text or explicitly enable it.")
    if scenario == "small_person" and options["placement"] != "in_scene":
        raise ValueError("small_person replacement needs placement=in_scene to replace the source person in context.")
    if options["style_instructions"]:
        options["style_source"] = "explicit_text"
    elif any(reference["role"] == "style" for reference in references):
        options["style_source"] = "explicit_reference"
    elif options["use_builtin_style"]:
        references.append(load_builtin_style())
        options["style_source"] = "builtin_reference"
    else:
        options["style_source"] = "text_default"
    status = "planned"
    next_action = "Call Codex builtin imagegen with imagegen-request.json, then collect its new PNG."
    if scene_pending:
        status = "scene_choice_needed"
        next_action = (
            "The user explicitly requested scene mode. Ask the three options in scene-picker.json using "
            "a currently available native selection tool, or ordinary text if none is available. Wait for "
            "an explicit answer; never pick the first option or proceed on timeout. Create a new plan "
            "with entry_mode=scene, the answered scene_choice and a new output_dir. The explicit choice "
            "overrides scenario but never sets replace_real_person; record replacement permission "
            "explicitly only after the user has authorized the identified target."
        )
    elif scenario == "small_person" and not options["replace_real_person"]:
        status = "recommendation_needed"
        next_action = "Recommend keeping the small real person or request explicit replacement permission; no executable request exists."
    elif not options["inputs_reviewed"]:
        status = "needs_input_review"
        next_action = "Open and actually review source and reference images, then create a new plan with inputs_reviewed=true."
    elif options["style_selection"] == "needed":
        status = "style_choice_needed"
        next_action = (
            "First display the actual available candidate reference images in chat. Then pass style-picker.json "
            "to an available native selection tool; if none is available, ask the same question in ordinary text. "
            "Wait for an explicit answer; never select the first option or proceed on timeout. Put the chosen "
            "reference/use_for in a new config, set style_selection=resolved and use a new output_dir. "
            "Keep scenario/placement/background and replacement permission unchanged. Already confirmed styles "
            "or explicit delegation should use resolved/delegate without asking again."
        )
    source_record = file_record(source)
    paths = list(dict.fromkeys([str(source)] + [reference["path"] for reference in references]))
    prompt = compile_prompt(options, source, references, paths)
    job = {
        "schema_version": 1,
        "helper": "cool-chibi-photo/codex_job",
        "config_path": str(config_path),
        "profile_path": str(profile_path) if profile_path else None,
        "output_dir": str(output),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "created_at_ns": time.time_ns(),
        "source": source_record,
        "references": references,
        "style_source": options["style_source"],
        "options": options,
        "status": status,
        "scene_picker_path": str(output / "scene-picker.json") if status == "scene_choice_needed" else None,
        "style_picker_path": str(output / "style-picker.json") if status == "style_choice_needed" else None,
        "user_acceptance": "pending",
        "generation": {"state": "not_run", "request_path": str(output / "imagegen-request.json") if status == "planned" else None},
        "delivery": {"composition_required": options["edit_scope"] == "strict_subject", "final_image": None},
        "next_action": next_action,
    }
    output.mkdir(parents=True, exist_ok=True)
    if status == "planned":
        request = {"prompt": prompt, "referenced_image_paths": paths,
                   "transparent_background": options["edit_scope"] == "strict_subject"}
        write_new(output / "prompt.txt", prompt)
        write_new(output / "imagegen-request.json", request)
    elif status == "style_choice_needed":
        picker = {"questions": [{
            "title": "这张照片想用哪种Q版画风？请选择上方实际候选参考图对应的一项；本次只选画风，场景、位置、背景与删人许可沿用已有选择。",
            "options": [entry["label"] + ("：" + entry["description"] if entry.get("description") else "")
                        for entry in options["style_options"]],
        }]}
        write_new(output / "style-picker.json", picker)
    elif status == "scene_choice_needed":
        picker = {"questions": [{
            "title": "这张图想用哪种场景版？请选择一项；选画风与删人许可会分别处理。",
            "options": [
                "没拍到我：把指定Q版加入风景或合适的场景位置",
                "宠物小物互动：保留真实宠物或物件，让Q版与它互动",
                "人太小替换：将指定小真人换成Q版，先明确替换目标与授权",
            ],
        }]}
        write_new(output / "scene-picker.json", picker)
    write_new(output / "job.json", job)
    return {"job": str(output / "job.json"), "status": status, "next_action": next_action,
            "request": job["generation"]["request_path"], "style_picker": job["style_picker_path"],
            "scene_picker": job["scene_picker_path"]}


def inspect_png(path: Path) -> dict[str, Any]:
    """Check PNG framing, chunk CRCs, IHDR size and IDAT presence, not pixel content."""
    if path.suffix.lower() != ".png":
        raise ValueError("Generated result must be a .png file.")
    data = path.read_bytes()
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("Generated result is not a PNG.")
    cursor, header, has_idat, has_trns = 8, None, False, False
    while cursor < len(data):
        if cursor + 12 > len(data):
            raise ValueError("Truncated PNG chunk.")
        length = struct.unpack(">I", data[cursor:cursor + 4])[0]
        kind = data[cursor + 4:cursor + 8]
        end = cursor + 12 + length
        if end > len(data):
            raise ValueError("Truncated PNG chunk payload.")
        payload = data[cursor + 8:cursor + 8 + length]
        expected = struct.unpack(">I", data[cursor + 8 + length:end])[0]
        if zlib.crc32(kind + payload) & 0xffffffff != expected:
            raise ValueError("PNG chunk CRC mismatch.")
        if header is None:
            if kind != b"IHDR" or length != 13:
                raise ValueError("PNG must begin with a valid IHDR.")
            width, height, depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
            if not (0 < width < 2 ** 31 and 0 < height < 2 ** 31) or depth not in depths.get(color_type, set()) or compression or filtering or interlace not in {0, 1}:
                raise ValueError("Invalid PNG IHDR values.")
            header = {"format": "PNG", "width": width, "height": height,
                      "bit_depth": depth, "color_type": color_type}
        elif kind == b"IHDR":
            raise ValueError("Duplicate PNG IHDR.")
        has_idat = has_idat or kind == b"IDAT"
        has_trns = has_trns or kind == b"tRNS"
        cursor = end
        if kind == b"IEND":
            if length or cursor != len(data) or not has_idat:
                raise ValueError("PNG needs image data and a final empty IEND.")
            return {**header, "has_transparency_metadata": header["color_type"] in {4, 6} or has_trns,
                    "chunk_crc_checked": True, "pixel_decode_checked": False,
                    "alpha_pixel_values_checked": False}
    raise ValueError("PNG has no final IEND.")


def collect(job_path: Path, result: Path, visual_review: Path | None = None) -> dict[str, Any]:
    job_path = job_path.expanduser().resolve()
    job = read_object(job_path)
    output = job_path.parent
    if job.get("schema_version") != 1 or job.get("helper") != "cool-chibi-photo/codex_job":
        raise ValueError("Not a codex_job plan.")
    if Path(job["output_dir"]).resolve() != output:
        raise ValueError("job.json must remain in its planned output_dir.")
    if job.get("status") != "planned" or job.get("generation", {}).get("state") != "not_run":
        raise ValueError("Only an executable, uncollected planned job can collect a result.")
    inputs = [job["source"], *job["references"]]
    for record in inputs:
        path = Path(record["path"])
        if not path.is_file() or digest(path) != record["sha256"]:
            raise ValueError(f"Source/reference changed or missing since planning: {path}")
    result = result.expanduser().resolve()
    if not result.is_file():
        raise ValueError(f"Generated result does not exist: {result}")
    if result in [Path(record["path"]).resolve() for record in inputs]:
        raise ValueError("Cannot collect a source/reference as a new generated result.")
    if result.stat().st_mtime_ns < job["created_at_ns"]:
        raise ValueError("Result predates this plan; use a newly generated PNG, not an old output.")
    result_hash = digest(result)
    if result_hash in {record["sha256"] for record in inputs}:
        raise ValueError("Result is an unchanged copy of a source/reference, not a new generated output.")
    png = inspect_png(result)
    strict = job["options"]["edit_scope"] == "strict_subject"
    if strict and not png["has_transparency_metadata"]:
        raise ValueError("strict_subject requires a transparent PNG asset (alpha/tRNS metadata missing).")
    review_record = None
    if visual_review:
        visual_review = visual_review.expanduser().resolve()
        report = read_object(visual_review)
        review_record = {**file_record(visual_review), "report": report,
                         "note": "User/Agent supplied review copied verbatim; helper did not inspect images or infer a pass."}
    destination = output / ("chibi.png" if strict else "final.png")
    qa_path, review_path = output / "qa.json", output / "visual-review.json"
    destinations = [destination, qa_path] + ([review_path] if visual_review else [])
    for path in destinations:
        if path.exists() or path.resolve() in [result, visual_review, *(Path(record["path"]).resolve() for record in inputs)]:
            raise ValueError(f"Refusing to overwrite any existing output/input: {path}")
    # Exclusive creation prevents accidental replacement even if another process races.
    with result.open("rb") as source_stream, destination.open("xb") as output_stream:
        shutil.copyfileobj(source_stream, output_stream)
    if digest(destination) != result_hash:
        destination.unlink()
        raise ValueError("Generated result changed while copying; nothing was collected.")
    if visual_review:
        with visual_review.open("rb") as source_stream, review_path.open("xb") as output_stream:
            shutil.copyfileobj(source_stream, output_stream)
        if digest(review_path) != review_record["sha256"]:
            review_path.unlink()
            destination.unlink()
            raise ValueError("Visual review changed while copying; nothing was collected.")
    technical = {"source_and_reference_hashes": "pass", "copy_sha256": "pass", "png_structure": png,
                 "likeness_pose_style_text_anatomy": "not_checked_requires_visual_review",
                 "strict_subject_preservation_verified": False}
    delivery = {"stage": "asset_ready_needs_composition" if strict else "image_ready_for_review",
                "artifact": str(destination), "composition_required": strict,
                "final_image": None if strict else str(destination),
                "strict_subject_preservation_verified": False}
    qa = {"status": "ready_for_user_review", "technical_checks": technical,
          "visual_review": review_record or {"status": "pending", "note": "No visual review provided; no automatic visual pass."},
          "delivery": delivery, "user_acceptance": "pending"}
    write_new(qa_path, qa)
    job["status"] = "ready_for_user_review"
    job["user_acceptance"] = "pending"
    job["generation"] = {**job["generation"], "state": "result_collected",
                         "result_origin": str(result), "result_sha256": result_hash,
                         "collected_at": datetime.now(timezone.utc).isoformat()}
    job["delivery"] = delivery
    job["qa_path"] = str(qa_path)
    job["next_action"] = "Compose the transparent asset with original foreground/masks, then verify-lock and review the final image." if strict else "Review visual quality with the user; user acceptance remains pending."
    # Updating this helper's own job record is intentional; image/input outputs remain exclusive.
    job_path.write_text(json.dumps(job, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"job": str(job_path), "artifact": str(destination), "qa": str(qa_path),
            "status": job["status"], "composition_required": strict, "user_acceptance": "pending"}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("doctor", help="Report helper capabilities; do not probe/call external APIs.")
    planning = commands.add_parser("plan", help="Compile prompt/request and create a new local job.")
    planning.add_argument("--config", type=Path, required=True)
    planning.add_argument("--profile", type=Path)
    collecting = commands.add_parser("collect", help="Copy a new builtin image result into its planned job.")
    collecting.add_argument("--job", type=Path, required=True)
    collecting.add_argument("--result", type=Path, required=True)
    collecting.add_argument("--visual-review", type=Path)
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            report = {"python": sys.version.split()[0], "python_supported": sys.version_info >= (3, 10),
                      "stdlib_only": True, "image_generation": "not_probed_use_current_Codex_builtin",
                      "network_calls": False, "image_editing": False,
                      "commands": ["doctor", "plan", "collect"],
                      "request_keys": ["prompt", "referenced_image_paths", "transparent_background"],
                      "note": "Doctor checks this helper only; it does not establish builtin tool access or image quality."}
        elif args.command == "plan":
            report = plan(args.config, args.profile)
        else:
            report = collect(args.job, args.result, args.visual_review)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError, struct.error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
