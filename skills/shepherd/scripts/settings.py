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


def add_hook(data, event, command, matcher):
    groups = data.setdefault("hooks", {}).setdefault(event, [])
    if any(h.get("command") == command for g in groups for h in g.get("hooks", [])):
        return data
    group = {"matcher": matcher} if matcher else {}
    group["hooks"] = [{"type": "command", "command": command}]
    groups.append(group)
    return data


def remove_hook(data, event, command, matcher):
    hooks = data.get("hooks", {})
    groups = []
    for group in hooks.get(event, []):
        group["hooks"] = [h for h in group.get("hooks", []) if h.get("command") != command]
        if group["hooks"]:
            groups.append(group)
    if groups:
        hooks[event] = groups
    else:
        hooks.pop(event, None)
    return data


