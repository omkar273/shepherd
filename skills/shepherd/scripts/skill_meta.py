"""Minimal metadata readers/writers for this repo's skills.

Two different parsers, because they serve different trust levels:
- parse_kv_block / format_kv_block: for .origin.yaml, which this repo's own
  tooling always writes in a fixed flat 'key: value' shape. No quoting, no
  block scalars.
- parse_frontmatter: for SKILL.md frontmatter, which is authored by many
  different tools/people and commonly uses quoted values or YAML folded
  block scalars (`key: >`) for long descriptions. This is NOT a general
  YAML parser - it only handles the subset seen in this repo's skills.
"""
import re
from pathlib import Path


def parse_kv_block(text):
    """Parse flat 'key: value' lines into a dict, splitting only on the
    FIRST ':' so values containing ':' (like URLs) stay intact. Blank
    lines and '#' comments are ignored. An empty value (e.g. 'key:' or
    'key: ') parses to '' rather than being dropped."""
    result = {}
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        result[key.strip()] = value.strip()
    return result


