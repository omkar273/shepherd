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

    def test_add_hook_idempotent(self):
        self.add("--write")
        result = self.add("--write")
        self.assertEqual(result.stdout.strip(), "")
        self.assertEqual(len(self.hooks()), 1)

    def test_keeps_other_keys(self):
        self.settings.write_text(json.dumps({"model": "opus", "hooks": {"Stop": [{"hooks": []}]}}))
        self.add("--write")
        data = json.loads(self.settings.read_text())
        self.assertEqual(data["model"], "opus")
        self.assertIn("Stop", data["hooks"])

    def test_invalid_json_exit1_untouched(self):
        self.settings.write_text("{not json")
        self.assertEqual(self.add("--write").returncode, 1)
        self.assertEqual(self.settings.read_text(), "{not json")

    def test_no_write_without_flag(self):
        result = self.add()
        self.assertIn("SessionStart", result.stdout)
        self.assertFalse(self.settings.exists())

    def test_remove_hook(self):
        self.add("--write")
        run("settings.py", self.home, "remove-hook", "--event", "SessionStart",
            "--command", CMD, "--write")
        self.assertNotIn("SessionStart", json.loads(self.settings.read_text()).get("hooks", {}))


class NudgeTests(Base):
    def nudge(self):
        return run("nudge.py", self.home)

    def stamp(self, days_ago):
        day = datetime.date.today() - datetime.timedelta(days=days_ago)
        self.state.write_text(json.dumps({"repo": "/r", "last_update": day.isoformat()}))

    def test_stale_prints_line(self):
        self.stamp(9)
        self.assertEqual(self.nudge().stdout.strip(),
                         'Skills last updated 9 days ago. Say "update my skills".')

