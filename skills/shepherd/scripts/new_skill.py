#!/usr/bin/env python3
"""Scaffold a new skill directory under skills/, with an .origin.yaml
provenance file. Use --seed-from to copy in real content from an existing
skill directory instead of writing a TODO stub."""
import argparse
import datetime
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_meta

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

STUB_TEMPLATE = """---
name: {name}
description: TODO - one-line description of when to use this skill
---

# {title}

TODO: describe what this skill does and how to use it.
"""


