#!/usr/bin/env python3
"""SessionStart hook: one line when skills were last updated over 7 days ago.

Reads ~/.claude/shepherd.json. Silent when the state is fresh, missing or
unreadable. Never fails, never touches the network."""
import argparse
import datetime
import json
from pathlib import Path

STALE_AFTER_DAYS = 7


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default=str(Path.home()))
    args = parser.parse_args()
    try:
        state = json.loads((Path(args.home).expanduser() / ".claude" / "shepherd.json").read_text())
        days = (datetime.date.today() - datetime.date.fromisoformat(state["last_update"])).days
    except (OSError, ValueError, KeyError, TypeError):
        return
    if days > STALE_AFTER_DAYS:
        print(f'Skills last updated {days} days ago. Say "update my skills".')


if __name__ == "__main__":
    main()
