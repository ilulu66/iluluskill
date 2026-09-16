#!/usr/bin/env python3
"""Install this skill locally; does not install packages, call APIs or change Codex config."""
from __future__ import annotations
import argparse
from datetime import datetime
from pathlib import Path
import shutil
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, help='Use PROJECT/.agents/skills instead of ~/.agents/skills.')
    parser.add_argument('--replace', action='store_true', help='Back up an existing same-name folder before installing.')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[1]
    home = (args.project.expanduser().resolve() if args.project else Path.home()) / '.agents'
    target = home / 'skills' / source.name
    stamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    backup = home / 'skill-backups' / f'{source.name}_{stamp}'
    try:
        if target.is_symlink():
            raise ValueError('Existing skill is a symlink. Inspect it manually; refusing automatic replacement.')
        if target.resolve() == source:
            print(f'Already located at: {target}')
            return 0
        if target.exists() and not args.replace:
            raise ValueError(f'{target} already exists. Use --replace to back up then replace it.')
        if target.exists() and not target.is_dir():
            raise ValueError(f'Target is not a directory: {target}')
        if not (source / 'SKILL.md').is_file():
            raise ValueError('Missing source SKILL.md.')
        print(f'Source: {source}\nTarget: {target}')
        if target.exists():
            print(f'Backup outside active skills: {backup}')
        if args.dry_run:
            print('Dry run only. No files changed.')
            return 0
        # Stage copy before touching the existing install.
        target.parent.mkdir(parents=True, exist_ok=True)
        staging = home / 'skill-install-staging' / f'{source.name}_{stamp}'
        staging.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source, staging, ignore=shutil.ignore_patterns(
            '__pycache__', '*.pyc', '.DS_Store', '.git', '.venv', 'venv',
            '.env', '.env.*', '00-协作台账.md', 'input', 'output', 'work', 'runs', 'tmp'))
        moved = False
        try:
            if target.exists():
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(target), str(backup))
                moved = True
            shutil.move(str(staging), str(target))
        except Exception:
            if moved and not target.exists() and backup.exists():
                shutil.move(str(backup), str(target))
            raise
        print(f'Installed: {target / "SKILL.md"}')
        print('Open a new Codex session and verify the skill is listed. This does not verify image tool access.')
        print('Check for older same-name skills in other active locations to avoid duplicate discovery.')
        return 0
    except (ValueError, OSError, shutil.Error) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
