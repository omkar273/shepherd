import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "link_skills.py"
SKILLS_DIR = Path(__file__).resolve().parents[3]
SKILL_COUNT = sum(1 for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").exists())


def run(home, *args):
    out = subprocess.run(
        [sys.executable, str(SCRIPT), "--home", str(home), *args],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)


def repo_links(runtime_dir):
    return [p for p in runtime_dir.iterdir()
            if p.is_symlink() and Path(os.path.realpath(p)).parent == SKILLS_DIR.resolve()]


def snapshot(root):
    return sorted((str(p.relative_to(root)), p.is_symlink()) for p in Path(root).rglob("*"))


