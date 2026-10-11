import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import skill_meta


class ParseKvBlockTests(unittest.TestCase):
    def test_parses_simple_pairs(self):
        text = "origin: mine\nsnapshotted_at: 2026-07-11\n"
        self.assertEqual(
            skill_meta.parse_kv_block(text),
            {"origin": "mine", "snapshotted_at": "2026-07-11"},
        )

