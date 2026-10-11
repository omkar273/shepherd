import datetime
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
SKILLS_DIR = Path(__file__).resolve().parents[3]
CMD = 'python3 "$HOME/.claude/skills/shepherd/scripts/nudge.py"'


def run(script, home, *args, check=True):
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args, "--home", str(home)],
        capture_output=True, text=True, check=check,
    )


