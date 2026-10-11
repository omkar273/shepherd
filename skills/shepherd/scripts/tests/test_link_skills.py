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


class LinkSkillsTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.claude = self.home / ".claude" / "skills"
        self.agents = self.home / ".agents" / "skills"

    def backups(self):
        return list((self.home / ".skills-backup").rglob("*"))

    def test_fresh_home_links_all(self):
        run(self.home)
        self.assertEqual(len(repo_links(self.claude)), SKILL_COUNT)
        self.assertEqual(len(repo_links(self.agents)), SKILL_COUNT)

    def test_real_dir_backed_up(self):
        (self.claude / "graphify").mkdir(parents=True)
        (self.claude / "graphify" / "old.txt").write_text("old")
        report = run(self.home)
        self.assertTrue((self.claude / "graphify").is_symlink())
        self.assertIn("claude/graphify", report["backed_up"])
        self.assertTrue(any(p.name == "old.txt" for p in self.backups()))

    def test_foreign_link_backed_up(self):
        elsewhere = self.home / "elsewhere"
        elsewhere.mkdir()
        self.agents.mkdir(parents=True)
        (self.agents / "shepherd").symlink_to(elsewhere)
        report = run(self.home)
        self.assertIn("agents/shepherd", report["backed_up"])
        self.assertEqual(Path(os.path.realpath(self.agents / "shepherd")), (SKILLS_DIR / "shepherd").resolve())

    def test_stale_repo_link_pruned(self):
        self.claude.mkdir(parents=True)
        (self.claude / "ghost").symlink_to(SKILLS_DIR / "ghost")
        report = run(self.home)
        self.assertFalse(os.path.lexists(self.claude / "ghost"))
        self.assertIn("claude/ghost", report["pruned"])

    def test_other_skill_untouched(self):
        (self.agents / "review").mkdir(parents=True)
        report = run(self.home)
        self.assertTrue((self.agents / "review").is_dir())
        self.assertFalse((self.agents / "review").is_symlink())
        self.assertIn("agents/review", report["untouched"])

    def test_dry_run_changes_nothing(self):
        (self.claude / "graphify").mkdir(parents=True)
        before = snapshot(self.home)
        report = run(self.home, "--dry-run", "--retire")
        self.assertEqual(snapshot(self.home), before)
        self.assertEqual(len(report["linked"]), 2 * SKILL_COUNT - 1)
        self.assertIn("claude/graphify", report["backed_up"])

    def test_second_run_noop(self):
        run(self.home, "--retire")
        report = run(self.home, "--retire")
        for key in ("linked", "backed_up", "pruned", "retired"):
            self.assertEqual(report[key], [], key)
        self.assertEqual(len(report["unchanged"]), 2 * SKILL_COUNT)

    def test_chained_link_backup_stays_valid(self):
        (self.claude / "lean").mkdir(parents=True)
        (self.claude / "lean" / "SKILL.md").write_text("old lean")
        self.agents.mkdir(parents=True)
        (self.agents / "lean").symlink_to(self.claude / "lean")
        run(self.home, "--retire")
        backup = next(p for p in (self.home / ".skills-backup").rglob("lean")
                      if p.parent.name == "agents")
        self.assertEqual((backup / "SKILL.md").read_text(), "old lean")

    def test_catalog_links_survive_relink(self):
        cache = self.home / ".shepherd" / "catalog" / "demo@abc1234"
        cache.mkdir(parents=True)
        self.claude.mkdir(parents=True)
        (self.claude / "demo").symlink_to(cache)
        report = run(self.home, "--retire")
        self.assertTrue((self.claude / "demo").is_symlink())
        self.assertIn("claude/demo", report["untouched"])

    def test_retired_real_dir_backed_up(self):
        (self.claude / "pricing-setup").mkdir(parents=True)
        report = run(self.home)
        self.assertIn("claude/pricing-setup", report["untouched"])
        report = run(self.home, "--retire")
        self.assertFalse(os.path.lexists(self.claude / "pricing-setup"))
        self.assertIn("claude/pricing-setup", report["retired"])


if __name__ == "__main__":
    unittest.main()
