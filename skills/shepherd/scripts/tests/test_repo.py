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

