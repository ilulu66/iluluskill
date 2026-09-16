#!/usr/bin/env python3
"""Validate the public photo-skill snapshot; never reads user photos or calls APIs."""
from __future__ import annotations
import argparse
import hashlib
import inspect
import importlib.util
import json
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1] / "skills" / "cool-chibi-photo"
EXCLUDED = {"__pycache__", ".venv", "venv", ".git", "input", "output", "work", "runs", "tmp"}
TEXT_SUFFIXES = {".md", ".txt", ".json", ".yaml", ".py"}


def distribution_files():
    result = []
    for directory, dirs, filenames in os.walk(ROOT):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDED)
        for name in sorted(filenames):
            path = Path(directory) / name
            if name in {"SHA256SUMS.txt", ".DS_Store", "00-协作台账.md"} or name.endswith(".pyc") or name.startswith(".env"):
                continue
            if path.is_symlink() or path.suffix not in TEXT_SUFFIXES:
                raise ValueError(f"Unexpected distributed asset: {path.relative_to(ROOT)}")
            result.append(path)
    return sorted(result)


def validate(write_manifest=False):
    files = distribution_files()
    for required in ["SKILL.md", "README.md", "LICENSE.md", "VALIDATION.md", "scripts/photo_ops.py", "scripts/install.py", "tests/test_photo_ops.py"]:
        if ROOT / required not in files:
            raise ValueError(f"Missing {required}")
    for path in files:
        content = path.read_text(encoding="utf-8")
        if re.search(r"/(?:Users|home)/[^\s\"']+", content):
            raise ValueError(f"Personal absolute path in {path.relative_to(ROOT)}")
        if re.search(r"(?:gh[opusr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{30,}|-----BEGIN (?:RSA |OPENSSH )?PRIVATE KEY-----)", content):
            raise ValueError(f"Possible credential in {path.relative_to(ROOT)}")
        if path.suffix == ".json":
            json.loads(content)
        if path.suffix == ".md":
            for link in re.findall(r"\]\(([^)]+)\)", content):
                if "://" in link or link.startswith("#"):
                    continue
                if not (path.parent / link.split("#")[0]).is_file():
                    raise ValueError(f"Broken local link in {path.name}: {link}")
    front = (ROOT / "SKILL.md").read_text().split("---", 2)[1]
    if not re.search(r"(?m)^name: cool-chibi-photo$", front):
        raise ValueError("Unexpected skill name")
    version = re.search(r'(?m)^  version: "([^"]+)"$', front)
    settings = json.loads((ROOT / "assets/settings.default.json").read_text())
    if version is None or version[1] != settings["skill_version"]:
        raise ValueError("Version mismatch")
    spec = importlib.util.spec_from_file_location("photo_ops", ROOT / "scripts/photo_ops.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    defaults = inspect.signature(module.compose_image).parameters
    for name in ["width_ratio", "min_width_ratio", "max_height_ratio", "max_inset_ratio"]:
        if defaults[name].default != settings["chibi"][name]:
            raise ValueError(f"Default mismatch: {name}")
    if defaults["margin_ratio"].default != settings["chibi"]["safe_margin_short_edge_ratio"]:
        raise ValueError("Margin default mismatch")
    manifest = "".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + p.relative_to(ROOT).as_posix() + "\n" for p in files)
    target = ROOT / "SHA256SUMS.txt"
    if write_manifest:
        target.write_text(manifest, encoding="utf-8")
    if not target.exists() or target.read_text() != manifest:
        raise ValueError("Manifest differs; inspect changes, then run --write-manifest")
    print(f"Public package valid: version {version[1]}, {len(files)} hashed files, examples/links/defaults checked.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-manifest", action="store_true", help="Refresh hashes after reviewing distribution changes.")
    args = parser.parse_args()
    validate(args.write_manifest)
