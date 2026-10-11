import json
import os
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


class InstallTests(TempDir):
    def setUp(self):
        super().setUp()
        src = self.tmp / "src"
        (src / "skills" / "demo").mkdir(parents=True)
        (src / "skills" / "demo" / "SKILL.md").write_text("---\nname: demo\n---\nhello\n")
        g = ["git", "-C", str(src), "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run(["git", "init", "-q", str(src)], check=True)
        subprocess.run(g + ["add", "-A"], check=True)
        subprocess.run(g + ["commit", "-q", "-m", "demo"], check=True)
        self.ref = subprocess.run(g + ["rev-parse", "HEAD"], capture_output=True, text=True, check=True).stdout.strip()
        self.src = src
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.claude = self.home / ".claude" / "skills"
        self.agents = self.home / ".agents" / "skills"

    def write_catalog(self, **overrides):
        skill = {"name": "demo", "repo": self.src.as_uri(), "path": "skills/demo", "ref": self.ref,
                 "sha256": catalog.content_hash(self.src / "skills" / "demo"), "license": "MIT",
                 "decision": "catalog/decisions/x.md"}
        skill.update(overrides)
        path = self.tmp / "catalog.json"
        path.write_text(json.dumps({"packs": {"demo-pack": {"domain": "D", "cues": ["c"], "skills": [skill]}}}))
        return path

    def run_cli(self, *args, cat=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args, "--home", str(self.home),
                               "--catalog", str(cat or self.write_catalog())], capture_output=True, text=True)

    def packs(self):
        return json.loads((self.home / ".claude" / "shepherd.json").read_text()).get("packs")

    def test_install_links_and_verifies(self):
        self.assertEqual(self.run_cli("install", "demo-pack").returncode, 0)
        for runtime in (self.claude, self.agents):
            self.assertTrue((runtime / "demo").is_symlink())
            self.assertIn("hello", (runtime / "demo" / "SKILL.md").read_text())
        self.assertEqual(self.packs(), ["demo-pack"])

    def test_install_tampered_refused(self):
        result = self.run_cli("install", "demo-pack", cat=self.write_catalog(sha256="0" * 64))
        self.assertEqual(result.returncode, 1)
        self.assertFalse(os.path.lexists(self.claude / "demo"))
        self.assertFalse(os.path.lexists(self.agents / "demo"))

    def test_install_missing_ref_links_nothing(self):
        result = self.run_cli("install", "demo-pack", cat=self.write_catalog(ref="c" * 40))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read", result.stderr)
        self.assertFalse(os.path.lexists(self.claude / "demo"))

    def test_install_backs_up_real_folder(self):
        (self.claude / "demo").mkdir(parents=True)
        (self.claude / "demo" / "old.txt").write_text("old")
        self.assertEqual(self.run_cli("install", "demo-pack").returncode, 0)
        self.assertTrue((self.claude / "demo").is_symlink())
        self.assertTrue(any(p.name == "old.txt" for p in (self.home / ".skills-backup").rglob("*")))

    def test_uninstall_removes_only_catalog_links(self):
        cat = self.write_catalog()
        self.run_cli("install", "demo-pack", cat=cat)
        (self.claude / "other").mkdir()
        self.assertEqual(self.run_cli("uninstall", "demo-pack", cat=cat).returncode, 0)
        self.assertFalse(os.path.lexists(self.claude / "demo"))
        self.assertFalse(os.path.lexists(self.agents / "demo"))
        self.assertTrue((self.claude / "other").is_dir())
        self.assertEqual(self.packs(), [])

    def test_prune_keeps_referenced_cache(self):
        cat = self.write_catalog()
        self.run_cli("install", "demo-pack", cat=cat)
        stale = self.home / ".shepherd" / "catalog" / "old@1234567"
        stale.mkdir(parents=True)
        self.assertEqual(self.run_cli("prune", cat=cat).returncode, 0)
        self.assertFalse(stale.exists())
        self.assertTrue((self.home / ".shepherd" / "catalog" / f"demo@{self.ref[:7]}").is_dir())

    def test_fetch_cli_copies_path_at_ref(self):
        dest = self.tmp / "fetched"
        result = subprocess.run([sys.executable, str(SCRIPT), "fetch", self.src.as_uri(), self.ref,
                                 "skills/demo", str(dest)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(catalog.content_hash(dest), catalog.content_hash(self.src / "skills" / "demo"))


if __name__ == "__main__":
    unittest.main()
