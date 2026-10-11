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


class Base(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        (self.home / ".claude").mkdir()
        self.settings = self.home / ".claude" / "settings.json"
        self.state = self.home / ".claude" / "shepherd.json"


class SettingsTests(Base):
    def add(self, *extra):
        return run("settings.py", self.home, "add-hook", "--event", "SessionStart",
                   "--command", CMD, *extra, check=False)

    def hooks(self):
        return json.loads(self.settings.read_text())["hooks"]["SessionStart"]

    def test_add_hook_to_empty(self):
        self.assertEqual(self.add("--write").returncode, 0)
        self.assertEqual(self.hooks(), [{"hooks": [{"type": "command", "command": CMD}]}])

