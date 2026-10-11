#!/usr/bin/env python3
"""Refresh a skill's content from its recorded .origin.yaml source.

Local filesystem sources (source_repo is a path) are copied directly.
Remote sources (source_repo is a git URL) are shallow-cloned into a
scratch directory first. source_repo == 'local' means nothing to sync.
"""
import argparse
import datetime
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_meta


def is_remote(source_repo):
    return (
        source_repo.startswith("http://")
        or source_repo.startswith("https://")
        or source_repo.startswith("git@")
    )


def clone_shallow(url, dest):
    subprocess.run(["git", "clone", "--depth", "1", url, str(dest)], check=True)


def git_short_head(path):
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    return result.stdout.strip()


