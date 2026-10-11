import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "claude_md.py"
BLOCK = (Path(__file__).resolve().parents[4] / "setup" / "claude-md.md").read_text()
BEGIN = "<!-- skills:begin -->"
END = "<!-- skills:end -->"


class ClaudeMdTests(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.path = self.home / ".claude" / "CLAUDE.md"

    def run_script(self):
        subprocess.run([sys.executable, str(SCRIPT), "--home", str(self.home)], check=True)
        return self.path.read_text()

    def test_creates_file(self):
        text = self.run_script()
        self.assertEqual(text, f"{BEGIN}\n{BLOCK}{END}\n")

    def test_inserts_block_with_markers(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text("# Mine\n\nkeep me\n")
        text = self.run_script()
        self.assertTrue(text.startswith("# Mine\n\nkeep me\n"))
        self.assertEqual(text.count(BEGIN), 1)
        self.assertIn(BLOCK, text)

    def test_replaces_existing_block(self):
        self.path.parent.mkdir(parents=True)
        self.path.write_text(f"top\n{BEGIN}\nold block\n{END}\nbottom\n")
        text = self.run_script()
        self.assertNotIn("old block", text)
        self.assertEqual(text.count(BEGIN), 1)
        self.assertIn(BLOCK, text)

    def test_bytes_outside_block_unchanged(self):
        before, after = "top line\n\n", "\nbottom line\nno newline at end"
        self.path.parent.mkdir(parents=True)
        self.path.write_text(f"{before}{BEGIN}\nold\n{END}{after}")
        text = self.run_script()
        self.assertTrue(text.startswith(before))
        self.assertTrue(text.endswith(after))
        self.assertEqual(self.run_script(), text)


if __name__ == "__main__":
    unittest.main()
