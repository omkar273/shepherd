#!/usr/bin/env python3
"""Write setup/claude-md.md into ~/.claude/CLAUDE.md between managed markers.

An existing managed block is replaced; everything outside it is kept
byte for byte. Without a block, one is appended."""
import argparse
from pathlib import Path

BLOCK_FILE = Path(__file__).resolve().parents[3] / "setup" / "claude-md.md"
BEGIN = "<!-- skills:begin -->"
END = "<!-- skills:end -->"


