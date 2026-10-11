import datetime
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent
SKILLS_DIR = Path(__file__).resolve().parents[3]
CMD = 'python3 "$HOME/.claude/skills/shepherd/scripts/nudge.py"'


