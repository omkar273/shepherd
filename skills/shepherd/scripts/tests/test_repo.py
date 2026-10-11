import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import gen_catalog
import skill_meta
import sync_skill

SKILLS_DIR = Path(__file__).resolve().parents[3]
README = SKILLS_DIR.parent / "README.md"

MATT = {
    "ask-matt", "codebase-design", "domain-modeling", "grill-with-docs", "implement",
    "implement-spec", "improve-codebase-architecture", "pr", "prototype", "research",
    "retro", "setup-matt-pocock-skills", "to-spec", "to-tickets", "triage", "wayfinder",
    "wizard", "grill-me", "grilling", "handoff", "teach", "to-questionnaire", "wait-what",
    "writing-for-agents", "git-guardrails-claude-code", "setup-pre-commit",
}
OTHERS = {"frontend-design", "ui-ux-pro-max", "graphify"}


def skill_dirs():
    return [p for p in sorted(SKILLS_DIR.iterdir()) if (p / "SKILL.md").exists()]


class RepoTests(unittest.TestCase):
    def test_expected_skills_present(self):
        names = {p.name for p in skill_dirs()}
        self.assertEqual(MATT | OTHERS, (MATT | OTHERS) & names)

    def test_skill_names_match_folders(self):
        for skill_dir in skill_dirs():
            name = skill_meta.read_skill_frontmatter(skill_dir).get("name")
            self.assertEqual(name, skill_dir.name, skill_dir)

    def test_no_duplicate_names(self):
        names = [skill_meta.read_skill_frontmatter(p).get("name") for p in skill_dirs()]
        self.assertEqual(len(names), len(set(names)))

    def test_vendored_origin_complete(self):
        for skill_dir in skill_dirs():
            if skill_dir.name == "shepherd":
                continue
            origin = skill_meta.read_origin(skill_dir)
            self.assertEqual(origin.get("origin"), "vendored", skill_dir)
            self.assertTrue(origin.get("source_repo"), skill_dir)
            if sync_skill.is_remote(origin["source_repo"]):
                self.assertTrue(origin.get("source_path"), skill_dir)
                self.assertTrue(origin.get("source_ref"), skill_dir)

    def test_catalog_current(self):
        text = README.read_text()
        _, rest = text.split(gen_catalog.START_MARKER, 1)
        current, _ = rest.split(gen_catalog.END_MARKER, 1)
        expected = gen_catalog.render_catalog(gen_catalog.collect_skills(SKILLS_DIR))
        self.assertEqual(current, f"\n\n{expected}\n\n")


SHEPHERD = SKILLS_DIR / "shepherd"


class ShepherdTests(unittest.TestCase):
    def test_shepherd_name(self):
        self.assertEqual(skill_meta.read_skill_frontmatter(SHEPHERD).get("name"), "shepherd")

    def test_thirty_skills(self):
        self.assertEqual(len(skill_dirs()), 30)

    def test_router_under_budget(self):
        self.assertLessEqual(len((SHEPHERD / "SKILL.md").read_text()) / 4, 5000)

    def test_routing_paths_exist(self):
        text = (SHEPHERD / "SKILL.md").read_text()
        paths = set(re.findall(r"`([a-z0-9_/-]+\.md)`", text))
        self.assertTrue(paths)
        missing = [p for p in sorted(paths) if not (SHEPHERD / p).exists()]
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
