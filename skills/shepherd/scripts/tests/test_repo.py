import re
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import catalog
import gen_catalog
import skill_meta
import sync_skill

SKILLS_DIR = Path(__file__).resolve().parents[3]
README = SKILLS_DIR.parent / "README.md"

CORE = {
    "shepherd", "codebase-design", "domain-modeling", "grilling", "pr", "prototype", "research",
    "wizard", "writing-for-agents", "git-guardrails-claude-code", "setup-pre-commit",
}


def skill_dirs():
    return [p for p in sorted(SKILLS_DIR.iterdir()) if (p / "SKILL.md").exists()]


class RepoTests(unittest.TestCase):
    def test_core_skills_present(self):
        self.assertEqual({p.name for p in skill_dirs()}, CORE)

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

    def test_router_under_budget(self):
        self.assertLessEqual(len((SHEPHERD / "SKILL.md").read_text()) / 4, 5000)

    def test_routing_paths_exist(self):
        text = (SHEPHERD / "SKILL.md").read_text()
        paths = set(re.findall(r"`([a-z0-9_/-]+\.md)`", text))
        self.assertTrue(paths)
        missing = [p for p in sorted(paths) if not (SHEPHERD / p).exists()]
        self.assertEqual(missing, [])

    def test_lang_files_keep_their_shape(self):
        # learn.md caps each lang file at 150 lines. Without `paths:`, a rule loads in every session.
        for path in sorted((SHEPHERD / "lang").glob("*.md")):
            text = path.read_text()
            self.assertLessEqual(len(text.splitlines()), 150, path.name)
            self.assertRegex(text, r'^---\npaths:\n(  - "[^"]+"\n)+---\n', path.name)
            headings = re.findall(r"^## (.+)$", text, re.M)
            self.assertEqual(headings, ["Keep", "Cut", "Boundaries", "Wiring"], path.name)
            for item in re.split(r"\n(?=- )", text):
                if item.startswith(("- **CRITICAL.**", "- **HIGH.**")):
                    self.assertIn("```", item, f"{path.name}: {item.splitlines()[0]}")

    def test_card_rules_match_the_skill(self):
        """A plugin-only install reads the rules from SKILL.md, a full setup from the card."""
        def section(text, heading):
            return re.search(rf"^#+ {heading}\n(.*?)(?=^#+ |\Z)", text, re.M | re.S).group(1).strip()

        skill = (SHEPHERD / "SKILL.md").read_text()
        card = (SKILLS_DIR.parent / "setup" / "claude-md.md").read_text()
        for card_heading, skill_heading in (("Write", "Write"), ("Never cut", "Never cut"),
                                            ("Cut list", "Shared cut list")):
            with self.subTest(card_heading):
                self.assertTrue(section(skill, skill_heading).startswith(section(card, card_heading)))


class CatalogRepoTests(unittest.TestCase):
    def router_pack_rows(self):
        text = (SHEPHERD / "skills.md").read_text()
        section = text.split("## Packs:", 1)[1].split("\n## ", 1)[0]
        rows = [l for l in section.splitlines() if l.startswith("| ") and not l.startswith("| Pack ")]
        return [r.split("|")[1].strip() for r in rows]

    def test_router_pack_names_exist_in_catalog(self):
        packs = catalog.load(catalog.CATALOG)["packs"]
        self.assertEqual([p for p in self.router_pack_rows() if p not in packs], [])

    def test_catalog_check_passes(self):
        self.assertEqual(catalog.check(catalog.load(catalog.CATALOG), catalog.REPO), [])

    def test_core_is_eleven(self):
        self.assertEqual(len(skill_dirs()), 11)


if __name__ == "__main__":
    unittest.main()
