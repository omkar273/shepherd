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

    def test_preserves_urls_with_colons(self):
        text = "source_repo: https://github.com/example/skills\n"
        self.assertEqual(
            skill_meta.parse_kv_block(text),
            {"source_repo": "https://github.com/example/skills"},
        )

    def test_ignores_blank_lines_and_comments(self):
        text = "# comment\norigin: mine\n\nsource_repo: local\n"
        self.assertEqual(
            skill_meta.parse_kv_block(text),
            {"origin": "mine", "source_repo": "local"},
        )

    def test_empty_values_round_trip_not_dropped(self):
        text = "source_path:\nsource_ref: \n"
        self.assertEqual(
            skill_meta.parse_kv_block(text),
            {"source_path": "", "source_ref": ""},
        )


