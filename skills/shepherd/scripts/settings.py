#!/usr/bin/env python3
"""Add or remove a command hook, or merge keys, in ~/.claude/settings.json.

--file targets another settings file, such as a repo's
.claude/settings.local.json. Prints a unified diff of the change and writes
only with --write. Other keys are kept. A null value in --json removes its
key. Exits 1, leaving the file untouched, when it isn't valid JSON."""
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


def merge(data, patch):
    for key, value in patch.items():
        if value is None:
            data.pop(key, None)
        elif isinstance(value, dict):
            data[key] = merge(data[key] if isinstance(data.get(key), dict) else {}, value)
        else:
            data[key] = value
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    for name in ("add-hook", "remove-hook", "merge"):
        p = sub.add_parser(name)
        if name == "merge":
            p.add_argument("--json", required=True, type=json.loads, help="object to merge in")
        else:
            p.add_argument("--event", required=True)
            p.add_argument("--command", required=True)
            p.add_argument("--matcher", default=None)
        p.add_argument("--file", default=None)
        p.add_argument("--write", action="store_true")
        p.add_argument("--home", default=str(Path.home()))
    args = parser.parse_args()

    path = (Path(args.file).expanduser() if args.file
            else Path(args.home).expanduser() / ".claude" / "settings.json")
    before = path.read_text() if path.exists() else ""
    try:
        data = json.loads(before) if before.strip() else {}
    except json.JSONDecodeError as error:
        sys.exit(f"settings.py: {path} is not valid JSON ({error}); left untouched")

    if args.action == "merge":
        data = merge(data, args.json)
    else:
        change = add_hook if args.action == "add-hook" else remove_hook
        data = change(data, args.event, args.command, args.matcher)
    after = render(data)
    if after == before:
        return
    sys.stdout.writelines(difflib.unified_diff(
        before.splitlines(keepends=True), after.splitlines(keepends=True),
        str(path), str(path)))
    if args.write:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(after)


if __name__ == "__main__":
    main()
