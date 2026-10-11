#!/usr/bin/env python3
"""Report drift between this repo and the installed skills, as JSON."""
import argparse
import datetime
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_meta
import sync_skill

SKILLS_DIR = Path(__file__).resolve().parents[2]
RUNTIMES = {"claude": Path(".claude/skills"), "agents": Path(".agents/skills")}


