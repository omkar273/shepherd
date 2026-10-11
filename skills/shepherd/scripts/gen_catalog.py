#!/usr/bin/env python3
"""Regenerate the skill catalog table in README.md from every skill's
SKILL.md frontmatter and .origin.yaml. Replaces only the content between
the <!-- CATALOG:START --> and <!-- CATALOG:END --> markers."""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_meta

START_MARKER = "<!-- CATALOG:START -->"
END_MARKER = "<!-- CATALOG:END -->"


