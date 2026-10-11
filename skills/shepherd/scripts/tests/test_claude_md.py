import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "claude_md.py"
BLOCK = (Path(__file__).resolve().parents[4] / "setup" / "claude-md.md").read_text()
BEGIN = "<!-- skills:begin -->"
END = "<!-- skills:end -->"


