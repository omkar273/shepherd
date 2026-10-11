#!/usr/bin/env python3
"""Claude Code hooks that keep a session's context small.

warn: UserPromptSubmit. One line when the session passes 40% of its context
      window, then 60%. The window size comes from the status line, else 200k.
trim: PostToolUse on Bash. Output over 200 lines goes to a log; Claude sees
      its first and last 60 lines. A command containing "# full" is exempt.
guard: PreToolUse on Bash. Denies a plain `cat FILE` or `sed -n '1,$p' FILE`
       of a text file over 300 lines.
statusline: the statusLine command. Prints "<model> | ctx <N>%" and records
            the window size for warn.

Each reads the hook's JSON on stdin. On any error it prints nothing and exits
0, so a broken hook never blocks or changes a session."""
import argparse
import itertools
import json
import re
import shlex
import shutil
import sys
import time
from pathlib import Path

THRESHOLDS = (40, 60)
DEFAULT_WINDOW = 200_000
MAX_LINES = 200
KEEP_LINES = 60
MAX_FILE_LINES = 300
FULL_VIEW_SED = re.compile(r"(1,\$)?p")
DUMP_REASON = "Use Read with an offset and limit, or `grep -n` then `sed -n 'a,bp'`."
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
    logs = session_dir(home, data)
    window = logs / "window"
    size = int(window.read_text()) if window.exists() else DEFAULT_WINDOW
    percent = 100 * tokens // size
    crossed = max([t for t in THRESHOLDS if percent >= t], default=0)
    if not crossed:
        return None
    state = logs / "warned"
    if state.exists() and int(state.read_text()) >= crossed:
        return None
    state.write_text(str(crossed))
    line = (f"Context is {percent}% full ({tokens // 1000}k of {size // 1000}k). If this is a "
            "new task, start a fresh session; otherwise `/compact` at the next task boundary.")
    return {"systemMessage": line,
            "hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": line}}


def trim(data, home):
    response = data["tool_response"]
    # persistedOutputPath: Claude Code saved the output itself and shows only a preview.
    if "# full" in data["tool_input"]["command"] or "persistedOutputPath" in response:
        return None
    streams = {name: response.get(name) or "" for name in ("stdout", "stderr")}
    if all(len(text.splitlines()) <= MAX_LINES for text in streams.values()):
        return None
    parts = [streams["stdout"]] if streams["stdout"] else []
    if streams["stderr"]:
        parts += ["[stderr]", streams["stderr"]]
    logs = session_dir(home, data)
    for n in itertools.count(len(list(logs.glob("*.log"))) + 1):
        log = logs / f"{n}.log"
        try:
            with open(log, "x", encoding="utf-8") as f:
                f.write("\n".join(parts) + "\n")
            break
        except FileExistsError:
            continue
    replaced = {}
    for name, text in streams.items():
        lines = text.splitlines()
        if len(lines) > MAX_LINES:
            marker = f"[{len(lines) - 2 * KEEP_LINES} lines trimmed; full log: {log}]"
            replaced[name] = "\n".join(lines[:KEEP_LINES] + [marker] + lines[-KEEP_LINES:])
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                   "updatedToolOutput": dict(response, **replaced)}}


def viewed_file(command):
    """The one file a plain `cat FILE` or `sed -n '1,$p' FILE` prints, else None."""
    lexer = shlex.shlex(command, posix=True, punctuation_chars=True)
    lexer.whitespace_split = True
    words = list(lexer)
    if any(set(word) <= set(lexer.punctuation_chars) for word in words):
        return None
    if words[:1] == ["cat"]:
        files = [word for word in words[1:] if not word.startswith("-")]
    elif len(words) == 4 and words[:2] == ["sed", "-n"] and FULL_VIEW_SED.fullmatch(words[2]):
        files = words[3:]
    else:
        return None
    return files[0] if len(files) == 1 else None


def guard(data, home):
    name = viewed_file(data["tool_input"]["command"])
    if name is None:
        return None
    path = Path(data["cwd"]) / Path(name).expanduser()
    # Not a FIFO or device: reading one could block the hook.
    if not path.is_file():
        return None
    with open(path, "rb") as f:
        if b"\0" in f.read(8192):
            return None
        f.seek(0)
        lines = sum(1 for _ in itertools.islice(f, MAX_FILE_LINES + 1))
    if lines <= MAX_FILE_LINES:
        return None
    return {"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                   "permissionDecisionReason": DUMP_REASON}}


def statusline(data, home):
    model = data["model"]["display_name"]
    context = data["context_window"]
    window = session_dir(home, data) / "window"
    size = str(context["context_window_size"])
    # Rewritten only on a change, so warn never reads it half-written.
    if not window.exists() or window.read_text() != size:
        window.write_text(size)
    percent = context.get("used_percentage")
    return model if percent is None else f"{model} | ctx {percent:.0f}%"


HOOKS = {"warn": warn, "trim": trim, "guard": guard, "statusline": statusline}


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
        print(result if isinstance(result, str) else json.dumps(result))


if __name__ == "__main__":
    main()
