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

