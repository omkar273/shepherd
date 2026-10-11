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
    skill = {"name": name, "repo": "file:///x", "path": f"skills/{name}", "license": "MIT",
             "decision": "catalog/decisions/x.md"}
    skill.update(overrides)
    return skill


class TempDir(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)


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

    def test_check_flags_missing_field(self):
        skill = entry("fresh")
        del skill["path"]
        self.assertTrue(any("path" in e for e in self.errors(skill)))

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
        self.src = self.tmp / "src"
        (self.src / "skills" / "demo").mkdir(parents=True)
        subprocess.run(["git", "init", "-q", str(self.src)], check=True)
        self.commit_skill("hello")
        self.home = self.tmp / "home"
        self.home.mkdir()
        self.claude = self.home / ".claude" / "skills"
        self.agents = self.home / ".agents" / "skills"

    def commit_skill(self, body):
        (self.src / "skills" / "demo" / "SKILL.md").write_text(f"---\nname: demo\n---\n{body}\n")
        g = ["git", "-C", str(self.src), "-c", "user.name=t", "-c", "user.email=t@example.com"]
        subprocess.run(g + ["add", "-A"], check=True)
        subprocess.run(g + ["commit", "-q", "-m", body], check=True)

    def write_catalog(self, **overrides):
        skill = {"name": "demo", "repo": self.src.as_uri(), "path": "skills/demo", "license": "MIT",
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

    def test_install_links_latest(self):
        self.assertEqual(self.run_cli("install", "demo-pack").returncode, 0)
        for runtime in (self.claude, self.agents):
            self.assertTrue((runtime / "demo").is_symlink())
            self.assertIn("hello", (runtime / "demo" / "SKILL.md").read_text())
        self.assertEqual(self.packs(), ["demo-pack"])

    def test_reinstall_refreshes_to_latest(self):
        cat = self.write_catalog()
        self.run_cli("install", "demo-pack", cat=cat)
        self.commit_skill("newer")
        self.assertEqual(self.run_cli("install", "demo-pack", cat=cat).returncode, 0)
        self.assertIn("newer", (self.claude / "demo" / "SKILL.md").read_text())

    def test_install_missing_path_links_nothing(self):
        result = self.run_cli("install", "demo-pack", cat=self.write_catalog(path="skills/nope"))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("cannot read", result.stderr)
        self.assertFalse(os.path.lexists(self.claude / "demo"))
        self.assertFalse(os.path.lexists(self.agents / "demo"))

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
        stale = self.home / ".shepherd" / "catalog" / "old"
        stale.mkdir(parents=True)
        self.assertEqual(self.run_cli("prune", cat=cat).returncode, 0)
        self.assertFalse(stale.exists())
        self.assertTrue((self.home / ".shepherd" / "catalog" / "demo").is_dir())

    def test_fetch_cli_copies_path_and_prints_commit(self):
        dest = self.tmp / "fetched"
        result = subprocess.run([sys.executable, str(SCRIPT), "fetch", self.src.as_uri(), "skills/demo", str(dest)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("hello", (dest / "SKILL.md").read_text())
        head = subprocess.run(["git", "-C", str(self.src), "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual(result.stdout.strip(), head)


if __name__ == "__main__":
    unittest.main()
