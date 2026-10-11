#!/usr/bin/env python3
"""Claude Code hooks that keep a session's context small.

warn: UserPromptSubmit. One line when the session passes 200k, then 400k.

Each reads the hook's JSON on stdin. On any error it prints nothing and exits
0, so a broken hook never blocks or changes a session."""
import argparse
import json
import re
import shutil
import sys
import time
from pathlib import Path

THRESHOLDS = (200_000, 400_000)
LOG_DAYS = 7
TRANSCRIPT_TAIL_BYTES = 4 * 1024 * 1024
SESSION_ID = re.compile(r"[A-Za-z0-9_-]+")


def session_dir(home, data):
    """Create ~/.claude/shepherd/logs/<session>; a new one prunes stale siblings."""
    session = data["session_id"]
    if not SESSION_ID.fullmatch(session):
        raise ValueError(f"unsafe session id: {session!r}")
    logs = home / ".claude" / "shepherd" / "logs"
    path = logs / session
    if not path.exists():
        cutoff = time.time() - LOG_DAYS * 86400
        for old in logs.glob("*"):
            if old.is_dir() and old.stat().st_mtime < cutoff:
                shutil.rmtree(old, ignore_errors=True)
        path.mkdir(parents=True)
    return path


def context_tokens(transcript):
    """Input tokens of the main thread's last request, read from the file's tail."""
    with open(transcript, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - TRANSCRIPT_TAIL_BYTES))
        lines = f.read().splitlines()
    for line in reversed(lines):
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("type") != "assistant" or entry.get("isSidechain"):
            continue
        usage = entry["message"].get("usage")
        if usage:
            return (usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
                    + usage.get("cache_creation_input_tokens", 0))
    return 0


def warn(data, home):
    tokens = context_tokens(Path(data["transcript_path"]))
    crossed = max([t for t in THRESHOLDS if tokens >= t], default=0)
    if not crossed:
        return None
    state = session_dir(home, data) / "warned"
    if state.exists() and int(state.read_text()) >= crossed:
        return None
    state.write_text(str(crossed))
    line = (f"Context is at {tokens // 1000}k. If this is a new task, start a fresh session; "
            "otherwise `/compact` at the next task boundary.")
    return {"systemMessage": line,
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": line}}


HOOKS = {"warn": warn}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hook", choices=HOOKS)
    parser.add_argument("--home", default=str(Path.home()))
    args = parser.parse_args()
    try:
        result = HOOKS[args.hook](json.load(sys.stdin), Path(args.home).expanduser())
    except Exception:
        return
    if result is not None:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
