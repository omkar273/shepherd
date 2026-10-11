import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import new_skill
import skill_meta


class NewSkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.skills_dir = Path(self.tmp) / "skills"
        self.skills_dir.mkdir()

    def test_creates_stub_skill_with_origin(self):
        skill_dir = new_skill.new_skill(
            "example-skill", "mine", skills_dir=self.skills_dir,
        )
        self.assertTrue((skill_dir / "SKILL.md").exists())
        self.assertIn("TODO", (skill_dir / "SKILL.md").read_text())
        origin = skill_meta.read_origin(skill_dir)
        self.assertEqual(origin["origin"], "mine")
        self.assertEqual(origin["source_repo"], "local")

    def test_rejects_invalid_name(self):
        with self.assertRaises(ValueError):
            new_skill.new_skill("Bad Name!", "mine", skills_dir=self.skills_dir)

