import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gen_catalog
import skill_meta


def make_skill(skills_dir, name, origin, description, source_repo="local"):
    skill_dir = Path(skills_dir) / name
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n"
    )
    skill_meta.write_origin(skill_dir, {
        "origin": origin, "source_repo": source_repo, "snapshotted_at": "2026-01-01",
    })


class CollectSkillsTests(unittest.TestCase):
    def test_collects_frontmatter_and_origin(self):
        with tempfile.TemporaryDirectory() as tmp:
            make_skill(tmp, "alpha", "mine", "Does alpha things.")
            make_skill(tmp, "beta", "vendored", "Does beta things.",
                       source_repo="https://example.com/beta")
            rows = gen_catalog.collect_skills(tmp)
            names = {row["name"] for row in rows}
            self.assertEqual(names, {"alpha", "beta"})

    def test_skips_dirs_without_skill_md(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "not-a-skill").mkdir()
            rows = gen_catalog.collect_skills(tmp)
            self.assertEqual(rows, [])


