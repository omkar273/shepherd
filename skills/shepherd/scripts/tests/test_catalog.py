import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import catalog

SCRIPT = Path(__file__).resolve().parent.parent / "catalog.py"


def entry(name, **overrides):
    skill = {"name": name, "repo": "file:///x", "path": f"skills/{name}", "ref": "a" * 40,
             "sha256": "b" * 64, "license": "MIT", "decision": "catalog/decisions/x.md"}
    skill.update(overrides)
    return skill


class TempDir(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


class HashTests(TempDir):
    def tree(self, name, files):
        root = self.tmp / name
        for rel, body in files:
            (root / rel).parent.mkdir(parents=True, exist_ok=True)
            (root / rel).write_text(body)
        return root

    def test_hash_stable_across_order(self):
        a = self.tree("a", [("SKILL.md", "x"), ("ref/one.md", "y")])
        b = self.tree("b", [("ref/one.md", "y"), ("SKILL.md", "x")])
        self.assertEqual(catalog.content_hash(a), catalog.content_hash(b))

    def test_hash_changes_on_byte_change(self):
        a = self.tree("a", [("SKILL.md", "x")])
        b = self.tree("b", [("SKILL.md", "x ")])
        self.assertNotEqual(catalog.content_hash(a), catalog.content_hash(b))

    def test_hash_ignores_dot_git(self):
        a = self.tree("a", [("SKILL.md", "x")])
        b = self.tree("b", [("SKILL.md", "x"), (".git/HEAD", "ref")])
        self.assertEqual(catalog.content_hash(a), catalog.content_hash(b))


class CheckTests(TempDir):
    def setUp(self):
        super().setUp()
        (self.tmp / "skills" / "core-one").mkdir(parents=True)
        (self.tmp / "skills" / "core-one" / "SKILL.md").write_text("---\nname: core-one\n---\n")
        (self.tmp / "setup").mkdir()
        (self.tmp / "setup" / "retired.txt").write_text("old-one\n")
        (self.tmp / "catalog" / "decisions").mkdir(parents=True)
        (self.tmp / "catalog" / "decisions" / "x.md").write_text("record")

    def errors(self, *skills):
        return catalog.check({"packs": {"p": {"domain": "D", "cues": ["c"], "skills": list(skills)}}}, self.tmp)

    def test_check_passes_valid_pack(self):
        self.assertEqual(self.errors(entry("fresh")), [])

    def test_check_passes_empty_catalog(self):
        self.assertEqual(catalog.check({"packs": {}}, self.tmp), [])

    def test_check_flags_short_ref(self):
        self.assertTrue(any("ref" in e for e in self.errors(entry("fresh", ref="abc123"))))

    def test_check_flags_duplicate_name(self):
        for name in ("core-one", "old-one"):
            with self.subTest(name):
                self.assertTrue(any("duplicate" in e for e in self.errors(entry(name))))
        self.assertTrue(any("duplicate" in e for e in self.errors(entry("twin"), entry("twin"))))

    def test_check_flags_missing_decision(self):
        errors = self.errors(entry("fresh", decision="catalog/decisions/nope.md"))
        self.assertTrue(any("decision" in e for e in errors))


class ListTests(TempDir):
    def test_list_marks_installed(self):
        cat = self.tmp / "catalog.json"
        cat.write_text(json.dumps({"packs": {
            "design": {"domain": "Design", "cues": ["UI"], "skills": [entry("a")]},
            "content": {"domain": "Content", "cues": ["post"], "skills": [entry("b")]},
        }}))
        home = self.tmp / "home"
        (home / ".claude").mkdir(parents=True)
        (home / ".claude" / "shepherd.json").write_text(json.dumps({"packs": ["design"]}))
        out = subprocess.run([sys.executable, str(SCRIPT), "list", "--home", str(home), "--catalog", str(cat)],
                             capture_output=True, text=True, check=True)
        listing = json.loads(out.stdout)
        self.assertTrue(listing["design"]["installed"])
        self.assertFalse(listing["content"]["installed"])
        self.assertEqual(listing["content"]["skills"], ["b"])


if __name__ == "__main__":
    unittest.main()
