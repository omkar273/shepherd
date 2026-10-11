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


def backup_path(home, runtime, name):
    base = home / ".skills-backup" / datetime.date.today().isoformat() / runtime / name
    candidate, n = base, 1
    while os.path.lexists(candidate):
        candidate = base.with_name(f"{name}-{n}")
        n += 1
    return candidate


def plan(home, retire):
    skills = sorted(p.name for p in SKILLS_DIR.iterdir() if (p / "SKILL.md").exists())
    retired = set(RETIRED_FILE.read_text().split()) if retire else set()
    report = {k: [] for k in ("linked", "unchanged", "backed_up", "pruned", "retired", "untouched")}
    actions = []
    for runtime, rel in RUNTIMES.items():
        runtime_dir = home / rel
        for name in skills:
            target, source = runtime_dir / name, SKILLS_DIR / name
            key = f"{runtime}/{name}"
            if target.is_symlink() and points_into_repo(target) and target.exists():
                report["unchanged"].append(key)
                continue
            if os.path.lexists(target):
                if target.is_symlink() and points_into_repo(target):
                    actions.append(("unlink", target, None))
                else:
                    report["backed_up"].append(key)
                    actions.append(("move", target, backup_path(home, runtime, name)))
            else:
                report["linked"].append(key)
            actions.append(("link", target, source))
        if not runtime_dir.is_dir():
            continue
        for entry in sorted(runtime_dir.iterdir()):
            key = f"{runtime}/{entry.name}"
            if entry.name in skills:
                continue
            if entry.is_symlink() and points_into_repo(entry):
                report["pruned"].append(key)
                actions.append(("unlink", entry, None))
            elif entry.name in retired:
                report["retired"].append(key)
                actions.append(("move", entry, backup_path(home, runtime, entry.name)))
            else:
                report["untouched"].append(key)
    return report, actions


def apply(actions):
    moved = {os.path.realpath(path): dest for kind, path, dest in actions
             if kind == "move" and not path.is_symlink()}
    for kind, path, other in actions:
        if kind == "unlink":
            path.unlink()
        elif kind == "move":
            other.parent.mkdir(parents=True, exist_ok=True)
            target = os.path.realpath(path) if path.is_symlink() else None
            if target in moved:
                other.symlink_to(moved[target], target_is_directory=True)
                path.unlink()
            else:
                os.rename(path, other)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.symlink_to(other, target_is_directory=True)


