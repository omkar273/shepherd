#!/usr/bin/env python3
"""Add or remove a command hook in ~/.claude/settings.json.

Prints a unified diff of the change and writes only with --write. Other keys
are kept. Exits 1, leaving the file untouched, when it isn't valid JSON."""
import argparse
import difflib
import json
import sys
from pathlib import Path


def render(data):
    return json.dumps(data, indent=2) + "\n"


