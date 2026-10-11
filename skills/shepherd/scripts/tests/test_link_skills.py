import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "link_skills.py"
SKILLS_DIR = Path(__file__).resolve().parents[3]
SKILL_COUNT = sum(1 for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").exists())


