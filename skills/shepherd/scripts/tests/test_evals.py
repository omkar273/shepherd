import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

EVALS = Path(__file__).resolve().parents[4] / "evals"
BUILD = EVALS / "build_fixture.sh"
CASES = {
    "go-billing": ("feat/void-invoices", "internal/service/void.go"),
    "ts-app": ("feat/apply-credit", "src/billing/credit.ts"),
    "ts-app-v2": (None, "src/billing/AGENTS.md"),
}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, check=True).stdout


class BuildFixtureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def build(self, name):
        dest = self.tmp / name
        subprocess.run(["bash", str(BUILD), name, str(dest)], capture_output=True, check=True)
        return dest

    def test_each_fixture_builds(self):
        for name, (branch, marker) in CASES.items():
            with self.subTest(name):
                repo = self.build(name)
                self.assertEqual(git(repo, "status", "--porcelain"), "")
                if branch:
                    self.assertIn(branch, git(repo, "branch", "--list", branch))
                    self.assertTrue(git(repo, "diff", "--stat", f"main...{branch}").strip())
                    git(repo, "show", f"{branch}:{marker}")
                else:
                    self.assertTrue((repo / marker).exists())

    def test_answer_key_names_every_fixture(self):
        key = (EVALS / "answer-key.md").read_text()
        for name in CASES:
            self.assertIn(name, key)


if __name__ == "__main__":
    unittest.main()
