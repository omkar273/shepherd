import shutil
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import sync_skill
import skill_meta


class ResolveSourceDirTests(unittest.TestCase):
    def test_local_sentinel_returns_none(self):
        src, git_root = sync_skill.resolve_source_dir({"source_repo": "local"}, workdir="/tmp")
        self.assertIsNone(src)
        self.assertIsNone(git_root)

    def test_local_path_resolves_with_source_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            (repo / "skills" / "example").mkdir(parents=True)
            src, git_root = sync_skill.resolve_source_dir(
                {"source_repo": str(repo), "source_path": "skills/example"},
                workdir=tmp,
            )
            self.assertEqual(src, repo / "skills" / "example")
            self.assertIsNone(git_root)

    def test_remote_url_triggers_clone(self):
        calls = []

        def fake_clone(url, dest):
            calls.append((url, dest))
            Path(dest).mkdir(parents=True)

        with tempfile.TemporaryDirectory() as tmp:
            src, git_root = sync_skill.resolve_source_dir(
                {"source_repo": "https://example.com/repo.git", "source_path": ""},
                workdir=tmp, clone=fake_clone,
            )
            self.assertEqual(len(calls), 1)
            self.assertEqual(src, git_root)

    def test_missing_local_path_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                sync_skill.resolve_source_dir(
                    {"source_repo": str(Path(tmp) / "does-not-exist")}, workdir=tmp,
                )


