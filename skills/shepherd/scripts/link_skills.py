#!/usr/bin/env python3
"""Link every skill in this repo into ~/.claude/skills and ~/.agents/skills.

A real folder or a foreign link in the way is moved to
~/.skills-backup/<date>/<runtime>/<name>, never deleted. Links into this repo
whose skill is gone are removed. With --retire, names in setup/retired.txt are
backed up too. Anything else is left alone. Prints a JSON report."""
import argparse
import datetime
import json
import os
from pathlib import Path

SKILLS_DIR = Path(__file__).resolve().parents[2]
RETIRED_FILE = SKILLS_DIR.parent / "setup" / "retired.txt"
RUNTIMES = {"claude": Path(".claude/skills"), "agents": Path(".agents/skills")}


def points_into_repo(path):
    return Path(os.path.realpath(path)).parent == SKILLS_DIR


