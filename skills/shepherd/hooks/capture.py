#!/usr/bin/env python3
"""Capture corrections to shepherd and print the lessons that apply.

turn     hook: append the prompt or the reply in stdin JSON to inbox/turns.jsonl
signal   record a correction; a clear repo lesson goes to lessons/repos/<slug>.md
lessons  print the global and repo lessons; pull in the background at most hourly
sync     pull or push, run detached by the commands above

Runs only from a full clone. Never calls a model; the only network use is the
detached git pull and push, each cut off after 5 seconds."""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEXT_BYTES = 4096
KEEP_DAYS = 30
EVIDENCE_CHARS = 200
REPO_CAP = 40
PULL_EVERY_SECONDS = 3600
GIT_TIMEOUT_SECONDS = 5
LESSON_KINDS = {"reject", "revert", "restore"}
LINE = re.compile(r"^- (?P<lesson>.+)\. \((?P<date>\d{4}-\d\d-\d\d), seen (?P<n>\d+)x\)$")

_NEVER_CUT = (r"(auth|authn|authz|authentication|authorization|permissions?|ownership|owner checks?"
              r"|tenant|scoping|balance|amount|money|state[- ](guard|check|machine)s?"
              r"|already[- ](paid|voided|void)|idempoten\w*|rollback|transactions?|clean-?up|defer"
              r"|finally|locks?|locking|version checks?)\b")
_NOT = r"(?<!never )(?<!not )(?<!don't )(?<!don’t )(?<!do not )"
_GAP = r"(?:\W+\w+){0,4}?\W+"
WEAKENS = re.compile(
    rf"{_NOT}\b(drop|remove|skip|cut|delete)\b{_GAP}{_NEVER_CUT}"
    rf"|\b{_NEVER_CUT}{_GAP}{_NOT}(dropped|removed|skipped|deleted|redundant|unnecessary|not needed)\b",
    re.IGNORECASE)


def weakens_never_cut(lesson):
    return bool(WEAKENS.search(lesson))


def full_clone(root):
    return (root.parent.parent / "setup" / "claude-md.md").is_file()


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


def append(path, entry):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def entry_ts(line):
    try:
        return json.loads(line)["ts"]
    except (ValueError, KeyError, TypeError):
        return ""


def prune(path, days):
    """Rewrite the file only when its oldest entry is past the cutoff."""
    cutoff = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=days)).isoformat(timespec="seconds")
    try:
        with path.open() as f:
            if entry_ts(f.readline()) >= cutoff:
                return
        kept = [l for l in path.read_text().splitlines(keepends=True) if entry_ts(l) >= cutoff]
    except OSError:
        return
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(kept))
    os.replace(tmp, path)


def turn(root):
    try:
        data = json.loads(sys.stdin.read())
        event = data["hook_event_name"]
        text = data.get("prompt") if event == "UserPromptSubmit" else data.get("last_assistant_message")
    except (ValueError, KeyError, TypeError, AttributeError):
        return
    if not isinstance(text, str) or not text:
        return
    path = root / "inbox" / "turns.jsonl"
    prune(path, KEEP_DAYS)
    append(path, {"ts": now(), "session_id": data.get("session_id"), "cwd": data.get("cwd"), "event": event,
                  "text": text.encode()[:TEXT_BYTES].decode(errors="ignore")})


def slug(repo_dir):
    url = git("remote", "get-url", "origin", cwd=repo_dir).stdout.strip()
    match = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    if match:
        name = f"{match[1]}-{match[2]}"
    else:
        top = git("rev-parse", "--show-toplevel", cwd=repo_dir).stdout.strip()
        name = Path(top or repo_dir).resolve().name
    return re.sub(r"[^A-Za-z0-9._-]", "-", name)


def spawn(root, direction):
    subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "sync", direction, "--root", str(root)],
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     start_new_session=True)


def sync(root, direction):
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    env.setdefault("GIT_SSH_COMMAND", "ssh -o BatchMode=yes")
    repos = root / "lessons" / "repos"
    targets = []
    if direction == "pull" and (root.parent.parent / ".git").exists():
        targets.append(root.parent.parent)
    if (repos / ".git").exists() and git("remote", cwd=repos).stdout.strip():
        targets.append(repos)
    command = ["pull", "--ff-only", "-q"] if direction == "pull" else ["push", "-q"]
    for cwd in targets:
        try:
            subprocess.run(["git", *command], cwd=cwd, env=env, capture_output=True, timeout=GIT_TIMEOUT_SECONDS)
        except (OSError, subprocess.TimeoutExpired):
            pass


def commit(root, path, message):
    repos = path.parent
    if not (repos / ".git").exists():
        git("init", "-q", cwd=repos)
        if not (repos / ".git").exists():
            return "not committed: git init failed"
    git("add", "--", path.name, cwd=repos)
    result = git("commit", "-q", "-m", message, "--", path.name, cwd=repos)
    if result.returncode:
        return "not committed: " + (result.stderr.strip().splitlines() or ["git commit failed"])[0]
    if git("remote", cwd=repos).stdout.strip():
        spawn(root, "push")
    return "committed"


def add_lesson(root, repo, lesson):
    path = root / "lessons" / "repos" / f"{repo}.md"
    lines = path.read_text().splitlines() if path.exists() else []
    for i, line in enumerate(lines):
        match = LINE.match(line)
        if match and match["lesson"].lower() == lesson.lower():
            lines[i] = f"- {match['lesson']}. ({match['date']}, seen {int(match['n']) + 1}x)"
            break
    else:
        if len(lines) >= REPO_CAP:
            return f'lessons/repos/{repo}.md is full ({REPO_CAP} lines): suggest "consolidate shepherd lessons"'
        lines.append(f"- {lesson}. ({datetime.date.today().isoformat()}, seen 1x)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    status = commit(root, path, f"lesson({repo}): {lesson}")
    note = f"lesson saved to lessons/repos/{repo}.md, {status} ({len(lines)}/{REPO_CAP} lines)"
    if len(lines) >= REPO_CAP:
        note += '; now full: suggest "consolidate shepherd lessons"'
    return note


def signal(root, args):
    if not full_clone(root):
        print("learning is off: shepherd is not running from a clone")
        return
    repo = slug(Path(args.repo_dir))
    lesson = (args.lesson or "").strip().rstrip(".")
    flag = args.flag or ("never-cut" if lesson and weakens_never_cut(lesson) else None)
    entry = {"ts": now(), "repo": repo, "kind": args.kind, "rule": args.rule,
             "evidence": (args.evidence.strip().splitlines() or [""])[0][:EVIDENCE_CHARS], "lesson": lesson}
    if flag:
        entry["flag"] = flag
    append(root / "inbox" / "signals.jsonl", entry)
    if flag:
        print("signal recorded; lesson not applied: it weakens the never-cut list. Tell the user.")
    elif lesson and args.kind in LESSON_KINDS:
        print(add_lesson(root, repo, lesson))
    else:
        print("signal recorded")


def lessons(root, repo_dir):
    if not full_clone(root):
        return
    stamp = root / "inbox" / "last-pull"
    try:
        due = time.time() - stamp.stat().st_mtime >= PULL_EVERY_SECONDS
    except OSError:
        due = True
    if due:
        stamp.parent.mkdir(parents=True, exist_ok=True)
        stamp.touch()
        spawn(root, "pull")
    repo = slug(Path(repo_dir))
    parts = []
    for title, path in (("global", root / "lessons" / "global.md"), (repo, root / "lessons" / "repos" / f"{repo}.md")):
        text = path.read_text().strip() if path.exists() else ""
        if text:
            parts.append(f"Lessons ({title}):\n{text}")
    if parts:
        print("\n\n".join(parts))


def main():
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--root", type=Path, default=ROOT)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("turn", parents=[common])
    sig = sub.add_parser("signal", parents=[common])
    sig.add_argument("--kind", required=True, choices=["reject", "revert", "restore", "accept"])
    sig.add_argument("--rule", required=True)
    sig.add_argument("--evidence", required=True, help="file:line and a one-line paraphrase; no secrets or code")
    sig.add_argument("--lesson")
    sig.add_argument("--flag", choices=["never-cut"])
    sig.add_argument("--repo-dir", default=".")
    les = sub.add_parser("lessons", parents=[common])
    les.add_argument("--repo-dir", default=".")
    syn = sub.add_parser("sync", parents=[common])
    syn.add_argument("direction", choices=["pull", "push"])
    args = parser.parse_args()
    root = args.root.resolve()

    if args.action == "turn":
        if full_clone(root):
            try:
                turn(root)
            except OSError:
                pass  # a hook must never fail the user's prompt
    elif args.action == "signal":
        signal(root, args)
    elif args.action == "lessons":
        lessons(root, args.repo_dir)
    else:
        sync(root, args.direction)


if __name__ == "__main__":
    main()
