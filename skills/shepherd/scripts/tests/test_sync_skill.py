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

