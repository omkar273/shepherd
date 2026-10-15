import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SHEPHERD = Path(__file__).resolve().parents[2]
SCRIPT = SHEPHERD / "scripts" / "review_context.py"
AGENTS = SHEPHERD / "agents"
GIT_ENV = {
    **os.environ, "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}


def frontmatter(path):
    block = path.read_text().split("---", 2)[1]
    return dict(line.split(": ", 1) for line in block.strip().splitlines())


class WiringTests(unittest.TestCase):
    """The review fork only works if review mode, the agents, and the script find each other."""

    def test_review_mode_spawns_the_reviewer(self):
        self.assertIn("`shepherd:reviewer`", (SHEPHERD / "code" / "review.md").read_text())
        self.assertEqual(frontmatter(AGENTS / "reviewer.md")["name"], "reviewer")

    def test_spawned_lenses_are_defined(self):
        reviewer = (AGENTS / "reviewer.md").read_text()
        self.assertIn("`shepherd:lens`", reviewer)
        self.assertEqual(frontmatter(AGENTS / "lens.md")["name"], "lens")
        lenses = re.findall(r"^### (\w+)$", (AGENTS / "lens.md").read_text(), re.M)
        spawned = re.findall(r"^   - `(\w+)`", reviewer, re.M)
        self.assertEqual(sorted(spawned), sorted(lenses))

    def test_plugin_root_paths_exist(self):
        for path in AGENTS.glob("*.md"):
            for rel in re.findall(r"\$\{CLAUDE_PLUGIN_ROOT\}/([\w./-]+[\w/])", path.read_text()):
                self.assertTrue((SHEPHERD / rel).exists(), f"{path.name}: {rel}")


class ReviewContextTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self.tmp.name)
        self.git("init", "-q", "-b", "main")
        (self.repo / "AGENTS.md").write_text("root rules\n")
        (self.repo / "api").mkdir()
        (self.repo / "api" / "AGENTS.md").write_text("api rules\n")
        (self.repo / "api" / "a.go").write_text("package api\n")
        self.git("add", ".")
        self.git("commit", "-qm", "base")
        self.git("checkout", "-qb", "feat/x")
        (self.repo / "api" / "a.go").write_text("package api\n\nfunc A() {}\n")
        self.git("commit", "-qam", "feat: add A")
        self.git("checkout", "-q", "main")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        subprocess.run(["git", *args], cwd=self.repo, env=GIT_ENV, check=True)

    def context(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=self.repo, env=GIT_ENV,
                              capture_output=True, text=True)

    def test_branch_and_base(self):
        out = self.context("feat/x", "main").stdout
        self.assertIn("Target: branch feat/x into main", out)
        self.assertIn("feat: add A", out)
        self.assertIn("AGENTS.md\napi/AGENTS.md", out)
        self.assertIn("+func A() {}", out)

    def test_extra_words_are_skipped(self):
        out = self.context("branch", "feat/x,", "base", "main").stdout
        self.assertIn("Target: branch feat/x into main", out)

    def test_never_checks_out(self):
        self.context("feat/x", "main")
        head = subprocess.run(["git", "branch", "--show-current"], cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(head.stdout.strip(), "main")

    def test_no_target_fails_with_usage(self):
        proc = self.context("please", "review", "it")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("No target found", proc.stderr)

    def test_option_like_words_are_ignored(self):
        proc = self.context("--output=/tmp/x", "feat/x", "main")
        self.assertIn("Target: branch feat/x into main", proc.stdout)


if __name__ == "__main__":
    unittest.main()
