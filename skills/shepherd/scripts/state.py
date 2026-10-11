#!/usr/bin/env python3
"""Record the repo path and today's date in ~/.claude/shepherd.json."""
import argparse
import datetime
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    stamp = sub.add_parser("stamp")
    stamp.add_argument("--repo", required=True)
    stamp.add_argument("--home", default=str(Path.home()))
    args = parser.parse_args()
    path = Path(args.home).expanduser() / ".claude" / "shepherd.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError):
        state = {}
    if not isinstance(state, dict):
        state = {}
    state.update(repo=args.repo, last_update=datetime.date.today().isoformat())
    path.write_text(json.dumps(state) + "\n")


if __name__ == "__main__":
    main()
