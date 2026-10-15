#!/usr/bin/env python3
"""Capture corrections to shepherd and print the lessons that apply.

turn     hook: append the prompt or the reply in stdin JSON to inbox/turns.jsonl,
         and remind the agent to record a prompt that looks like a correction;
         machine text (task notifications, system reminders, agent messages) is cut first
signal   record a correction or an accepted review; a clear repo lesson goes to
         lessons/repos/<slug>.md with a confidence, a citation, a seen count, and dates
lessons  print the global lessons and the top repo lessons whose citation still exists;
         archive repo lessons unused for 60 days; pull in the background at most hourly
report   print the data for "consolidate shepherd lessons": precision, rejects, proposals
step0    print the repo card (check commands, lint config, nested AGENTS.md), then
         the lessons; the card is cached until HEAD, the index, or a root file changes
sync     pull or push, run detached by the commands above

Learning runs only from a full clone; step0 prints the repo card anywhere.
Never calls a model; the only network use is the detached git pull and push,
each cut off after 5 seconds."""
import argparse
import datetime
import hashlib
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
CORRECTION = re.compile(
    r"\b(wrong|incorrect|(is|was|are|were) needed|not needed|(put|bring)\b[^.]{0,30}\bback"
    r"|undo|revert|restore|should(n't| not)? have|(don't|do not) (cut|remove|drop|flag)|keep (it|that|this|the))\b",
    re.IGNORECASE)
REMINDER = ("shepherd: if this message corrects your work, record it with "
            "`capture.py signal` before you reply (learn.md, Record a correction).")
# Text that the harness or another agent puts in a prompt. The user's own words stay.
MACHINE_TEXT = re.compile(
    r"\[SYSTEM NOTIFICATION\b.*?(?:\n\s*\n|\Z)"
    r"|<(task-notification|system-reminder|cross-session-message|agent-message|teammate-message"
    r"|side-sessions-event|ci-monitor-event)\b[^>]*>.*?(?:</\1>|\Z)", re.S)
LESSON_CAP = 8
EXPIRE_DAYS = 60
REFRESH_DAYS = 7  # write a new used date at most weekly, so a print rarely makes a commit
CONFIDENCE = {"reject": 0.6, "revert": 0.7, "restore": 0.8}
CONFIDENCE_STEP = 0.1
PROPOSE_AT = 3
OVERLAP = 0.8
ARCHIVE = "## Archive"
PROPOSE = ("seen {n}x: if a lint rule or a hook can check this lesson, propose one to the user "
           "(learn.md, Propose a check). Apply it only after a yes.")
CARD_DIR = Path.home() / ".claude" / "shepherd" / "repo-cards"
ROOT_FILES = ("package.json", "Makefile", "justfile", "pyproject.toml", "CLAUDE.md", "AGENTS.md")
LOCKFILES = (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("bun.lock", "bun"), ("bun.lockb", "bun"))
CHECK_NAME = re.compile(r"(^|[-_:.])(lint|tests?|check|typecheck|types|vet|fmt|format|build|ci|verify|knip)", re.I)
LINT_CONFIG = re.compile(
    r"^(\.?eslint[\w.]*|biome\.jsonc?|\.golangci\.ya?ml|\.?ruff\.toml|\.prettierrc[\w.]*|prettier\.config\.\w+"
    r"|tsconfig[\w.]*\.json|\.flake8|mypy\.ini|\.stylelintrc[\w.]*|rustfmt\.toml|clippy\.toml|deno\.jsonc?)$")
CARD_LIMIT = 12
LINE = re.compile(r"^- (?P<text>.+)\. \(conf (?P<conf>[\d.]+), seen (?P<seen>\d+)x, added (?P<added>\d{4}-\d\d-\d\d),"
                  r" used (?P<used>\d{4}-\d\d-\d\d)(?:, cite (?P<cite>\S+))?\)$")
OLD_LINE = re.compile(r"^- (?P<text>.+)\. \((?P<date>\d{4}-\d\d-\d\d), seen (?P<n>\d+)x\)$")
CITE = re.compile(r"^(?P<path>[\w./@\[\]+-]*[\w\]])(?::(?P<line>\d+))?$")

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
    if not isinstance(text, str):
        return
    if event == "UserPromptSubmit":
        text = MACHINE_TEXT.sub("", text).strip()
    if not text:
        return
    if event == "UserPromptSubmit" and CORRECTION.search(text):
        print(REMINDER)  # UserPromptSubmit stdout reaches the model as context
    path = root / "inbox" / "turns.jsonl"
    prune(path, KEEP_DAYS)
    append(path, {"ts": now(), "session_id": data.get("session_id"), "cwd": data.get("cwd"), "event": event,
                  "text": text.encode()[:TEXT_BYTES].decode(errors="ignore")})


def toplevel(repo_dir):
    top = git("rev-parse", "--show-toplevel", cwd=repo_dir).stdout.strip()
    return Path(top or repo_dir).resolve()


def slug(repo_dir):
    url = git("remote", "get-url", "origin", cwd=repo_dir).stdout.strip()
    match = re.search(r"[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$", url)
    name = f"{match[1]}-{match[2]}" if match else toplevel(repo_dir).name
    return re.sub(r"[^A-Za-z0-9._-]", "-", name)


def memory_dir(repo_dir):
    """Claude Code's auto memory for the repo: one folder for the main checkout and its worktrees."""
    common = git("rev-parse", "--path-format=absolute", "--git-common-dir", cwd=repo_dir).stdout.strip()
    project = Path(common).parent if common else toplevel(repo_dir)
    return Path.home() / ".claude" / "projects" / re.sub(r"[^A-Za-z0-9]", "-", str(project)) / "memory"


def content_words(text):
    return set(re.findall(r"[a-z][a-z0-9_]{3,}", text.lower()))


def memory_overlap(text, memory, repo):
    """The auto memory note that holds most of the lesson's words, when it holds OVERLAP of them or more."""
    words = content_words(text) - content_words(repo.replace("-", " "))
    notes = [p for p in sorted(memory.glob("*.md")) if p.name != "MEMORY.md"] if words else []
    share, name = max(((len(words & content_words(read(p))) / len(words), p.name) for p in notes), default=(0, ""))
    return name if share >= OVERLAP else None


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


def raised(conf, steps=1):
    return round(min(1.0, conf + CONFIDENCE_STEP * steps), 1)


def parse_lesson(line):
    if match := LINE.match(line):
        return {"text": match["text"], "conf": float(match["conf"]), "seen": int(match["seen"]),
                "added": match["added"], "used": match["used"], "cite": match["cite"]}
    if match := OLD_LINE.match(line):  # the format before 1.13; the next write migrates it
        seen = int(match["n"])
        return {"text": match["text"], "conf": raised(CONFIDENCE["reject"], seen - 1), "seen": seen,
                "added": match["date"], "used": match["date"], "cite": None}
    return {"raw": line}


def format_lesson(lesson):
    if "raw" in lesson:
        return lesson["raw"]
    cite = f", cite {lesson['cite']}" if lesson["cite"] else ""
    return (f"- {lesson['text']}. (conf {lesson['conf']:.1f}, seen {lesson['seen']}x, "
            f"added {lesson['added']}, used {lesson['used']}{cite})")


def read_lessons(path):
    """The active lessons and the archived lessons (the ones under ARCHIVE)."""
    active, archived = [], []
    part = active
    for line in read(path).splitlines():
        if line.strip() == ARCHIVE:
            part = archived
        elif line.strip():
            part.append(parse_lesson(line))
    return active, archived


def write_lessons(path, active, archived):
    lines = [format_lesson(lesson) for lesson in active]
    if archived:
        lines += ["", ARCHIVE, "", *(format_lesson(lesson) for lesson in archived)]
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("\n".join(lines) + "\n")
    os.replace(tmp, path)


def cited(top, cite):
    """True when the cited file is in the repo and, for path:line, has that line."""
    match = CITE.match(cite)
    if not match:
        return False
    path = (top / match["path"]).resolve()
    if not path.is_relative_to(top) or not path.is_file():
        return False
    return not match["line"] or len(read(path).splitlines()) >= int(match["line"])


def citation(top, evidence):
    """The file or file:line that starts the evidence, when that file is in the repo."""
    first = (evidence.split() or [""])[0].rstrip(",;:").removeprefix("./")
    return first if cited(top, first) else None


def add_lesson(root, repo, lesson, kind, cite):
    path = root / "lessons" / "repos" / f"{repo}.md"
    active, archived = read_lessons(path)
    today = datetime.date.today().isoformat()
    found = next((l for l in active + archived if l.get("text", "").lower() == lesson.lower()), None)
    if found:
        if any(l is found for l in archived):  # recorded again: the archived lesson comes back
            archived = [l for l in archived if l is not found]
            active.append(found)
        found.update(conf=raised(found["conf"]), seen=found["seen"] + 1, used=today, cite=cite or found["cite"])
    elif len(active) >= REPO_CAP:
        return f'lessons/repos/{repo}.md is full ({REPO_CAP} lines): suggest "consolidate shepherd lessons"'
    else:
        found = {"text": lesson, "conf": CONFIDENCE[kind], "seen": 1, "added": today, "used": today, "cite": cite}
        active.append(found)
    write_lessons(path, active, archived)
    status = commit(root, path, f"lesson({repo}): {lesson}")
    detail = f"conf {found['conf']:.1f}, seen {found['seen']}x, " + (f"cite {cite}" if cite else "no citation")
    note = f"lesson saved to lessons/repos/{repo}.md ({detail}), {status} ({len(active)}/{REPO_CAP} lines)"
    if len(active) >= REPO_CAP:
        note += '; now full: suggest "consolidate shepherd lessons"'
    if found["seen"] >= PROPOSE_AT:
        note += "\n" + PROPOSE.format(n=found["seen"])
    return note


def signal(root, args):
    if not full_clone(root):
        print("learning is off: shepherd is not running from a clone")
        return
    repo_dir = Path(args.repo_dir)
    repo = slug(repo_dir)
    lesson = (args.lesson or "").strip().rstrip(".")
    flag = args.flag or ("never-cut" if lesson and weakens_never_cut(lesson) else None)
    evidence = (args.evidence.strip().splitlines() or [""])[0][:EVIDENCE_CHARS]
    entry = {"ts": now(), "repo": repo, "kind": args.kind, "rule": args.rule, "evidence": evidence, "lesson": lesson}
    if args.kind == "accept":
        entry.update(posted=args.posted, dropped=args.dropped)
    if flag:
        entry["flag"] = flag
    append(root / "inbox" / "signals.jsonl", entry)
    if flag:
        print("signal recorded; lesson not applied: it weakens the never-cut list. Tell the user.")
    elif lesson and args.kind in LESSON_KINDS:
        print(add_lesson(root, repo, lesson, args.kind, citation(toplevel(repo_dir), evidence)))
        if note := memory_overlap(lesson, memory_dir(repo_dir), repo):
            print(f"auto memory has a similar note ({note}). Keep the lesson only if it changes a shepherd rule "
                  "or must sync to other machines (learn.md, Shepherd or auto memory). Tell the user.")
    else:
        print("signal recorded")


def days_between(first, last):
    return (datetime.date.fromisoformat(last) - datetime.date.fromisoformat(first)).days


def rank(lesson):
    return lesson.get("conf", 0.5), lesson.get("used", ""), lesson.get("seen", 1), lesson.get("added", "")


def use_lessons(root, repo, top):
    """Archive the unused lessons, then pick the top LESSON_CAP lessons whose citation still exists.

    A lesson is unused when its used date is EXPIRE_DAYS older than the newest used date in the
    file, so a repo that nobody opens keeps its lessons."""
    path = root / "lessons" / "repos" / f"{repo}.md"
    active, archived = read_lessons(path)
    dated = [lesson["used"] for lesson in active if "used" in lesson]
    clock = max(dated, default="")
    expired = [l for l in active if "used" in l and days_between(l["used"], clock) > EXPIRE_DAYS]
    active = [l for l in active if not any(l is e for e in expired)]
    valid = [l for l in active if not l.get("cite") or cited(top, l["cite"])]
    shown = sorted(valid, key=rank, reverse=True)[:LESSON_CAP]
    today = datetime.date.today().isoformat()
    marked = [l for l in shown if "used" in l and days_between(l["used"], today) >= REFRESH_DAYS]
    for lesson in marked:
        lesson["used"] = today
    if expired or marked:
        write_lessons(path, active, archived + expired)
        changes = [f"archive {len(expired)} unused" if expired else "", f"mark {len(marked)} used" if marked else ""]
        commit(root, path, f"lesson({repo}): {', '.join(filter(None, changes))}")
    hidden = [f"{len(valid) - len(shown)} below the cap of {LESSON_CAP}" if len(valid) > len(shown) else "",
              f"{len(active) - len(valid)} with a stale citation" if len(active) > len(valid) else "",
              f"{len(expired)} archived now, unused for {EXPIRE_DAYS} days" if expired else ""]
    return shown, list(filter(None, hidden))


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
    if text := read(root / "lessons" / "global.md").strip():
        parts.append(f"Lessons (global):\n{text}")
    shown, hidden = use_lessons(root, repo, toplevel(repo_dir))
    if shown:
        parts.append(f"Lessons ({repo}), by confidence and recent use:\n" + "\n".join(map(format_lesson, shown)))
    if hidden:
        parts.append(f"Not shown: {', '.join(hidden)}. To review them, say \"consolidate shepherd lessons\".")
    if parts:
        print("\n\n".join(parts))


def report(root, repo_dir):
    """The counts that "consolidate shepherd lessons" starts from. It changes no file."""
    if not full_clone(root):
        print("learning is off: shepherd is not running from a clone")
        return
    since = read(root / "inbox" / "last-consolidation").strip()
    signals = []
    for line in read(root / "inbox" / "signals.jsonl").splitlines():
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if entry.get("ts", "")[:10] >= since:
            signals.append(entry)
    kinds = {kind: sum(s.get("kind") == kind for s in signals) for kind in ("reject", "revert", "restore", "accept")}
    out = [f"Signals since {since or 'the start'}: {len(signals)} ("
           + ", ".join(f"{kind} {n}" for kind, n in kinds.items()) + ")"]
    reviews = [s for s in signals if s.get("kind") == "accept" and isinstance(s.get("posted"), int)]
    posted = sum(s["posted"] for s in reviews)
    drafted = posted + sum(s.get("dropped") or 0 for s in reviews)
    out.append(f"Review precision: {posted}/{drafted} drafted findings posted ({posted / drafted:.0%}) "
               f"in {len(reviews)} reviews" if drafted else "Review precision: no accepted reviews")
    rejects = {}
    for s in signals:
        if s.get("kind") == "reject":
            rejects[s.get("rule", "")] = rejects.get(s.get("rule", ""), 0) + 1
    narrow = [f"- {rule} ({n}x)" for rule, n in sorted(rejects.items(), key=lambda r: -r[1]) if n >= 3]
    out += ["Rules with 3 or more rejects (narrow them):", *narrow] if narrow else []
    flagged = [f"- {s.get('repo')}: {s.get('lesson') or s.get('evidence')}" for s in signals if s.get("flag")]
    out += ["Never-cut flags (never apply them):", *flagged] if flagged else []
    repo = slug(Path(repo_dir))
    top, memory = toplevel(repo_dir), memory_dir(repo_dir)
    proposals, stale, duplicates = [], [], []
    for path in sorted((root / "lessons" / "repos").glob("*.md")):
        active, archived = read_lessons(path)
        out.append(f"Lessons in {path.stem}: {len(active)} active, {len(archived)} archived")
        proposals += [f"- {path.stem}: {l['text']} ({l['seen']}x)" for l in active if l.get("seen", 0) >= PROPOSE_AT]
        if path.stem != repo:
            continue
        stale += [f"- {l['text']} (cite {l['cite']})" for l in active if l.get("cite") and not cited(top, l["cite"])]
        for lesson in active:
            if "text" in lesson and (note := memory_overlap(lesson["text"], memory, repo)):
                duplicates.append(f"- {lesson['text']} ({note})")
    out += [f"Check proposals: seen {PROPOSE_AT}x or more (learn.md, Propose a check):", *proposals] if proposals else []
    out += [f"Stale citations in {repo} (fix the citation or drop the lesson):", *stale] if stale else []
    out += [f"Auto memory has these {repo} lessons (learn.md, Shepherd or auto memory):", *duplicates] if duplicates else []
    print("\n".join(out))


def read(path):
    try:
        return path.read_text(errors="replace")
    except OSError:
        return ""


def check_commands(top, names):
    checks = []
    if "package.json" in names:
        try:
            scripts = json.loads(read(top / "package.json")).get("scripts") or {}
        except (ValueError, AttributeError):
            scripts = {}
        runner = next((tool for lock, tool in LOCKFILES if lock in names), "npm")
        checks += [f"{runner} run {name}: {str(cmd)[:80]}" for name, cmd in scripts.items() if CHECK_NAME.search(name)]
    for name, tool, target in (("Makefile", "make", r"^([A-Za-z_][\w.-]*)\s*:(?!=)"),
                               ("justfile", "just", r"^([A-Za-z_][\w-]*)[^:\n=]*:(?!=)")):
        if name in names:
            found = dict.fromkeys(re.findall(target, read(top / name), re.M))
            checks += [f"{tool} {t}" for t in found if CHECK_NAME.search(t)]
    for workflow in sorted((top / ".github" / "workflows").glob("*.y*ml")):
        lines = read(workflow).splitlines()
        for i, line in enumerate(lines):
            if match := re.match(r"^\s*(?:-\s*)?run:\s*(.*)$", line):
                cmd = match[1].strip()
                if cmd in ("|", ">", "|-", ">-"):
                    cmd = next((l.strip() for l in lines[i + 1:] if l.strip()), "")
                checks.append(f"CI {workflow.name}: {cmd[:100]}")
    return list(dict.fromkeys(checks))


def build_card(top):
    names = set(os.listdir(top))
    checks = check_commands(top, names)
    lint = sorted(n for n in names if LINT_CONFIG.match(n))
    tools = re.findall(r"^\[tool\.(ruff|mypy|pyright|pytest[\w.]*|black|isort)\]", read(top / "pyproject.toml"), re.M)
    lint += [f"pyproject.toml [tool.{t}]" for t in tools]
    listed = git("ls-files", "-z", "--cached", "--others", "--exclude-standard", "--",
                 ":(glob)**/AGENTS.md", ":(glob)**/CLAUDE.md", cwd=top).stdout.split("\0")
    nested = sorted({p for p in listed if "/" in p})
    skills = sorted(p.parent.name for p in (top / ".agents" / "skills").glob("*/SKILL.md"))
    lines = [f"Repo card for {top} (shepherd Step 0):", "Checks:"]
    lines += [f"- {c}" for c in checks[:CARD_LIMIT]] or ["- none found: read the repo docs"]
    if len(checks) > CARD_LIMIT:
        lines.append(f"- and {len(checks) - CARD_LIMIT} more")
    lines.append(f"Lint config: {', '.join(lint) or 'none found'}")
    lines.append("Nested AGENTS.md and CLAUDE.md: " + (", ".join(nested[:30]) or "none"))
    if skills:
        lines.append(f"Repo skills in .agents/skills: {', '.join(skills)}")
    if {"AGENTS.md", "CLAUDE.md"} <= names and "@AGENTS.md" not in read(top / "CLAUDE.md"):
        lines.append("Root AGENTS.md is not loaded: CLAUDE.md does not import it. Read it.")
    return "\n".join(lines)


def repo_card(repo_dir):
    """The repo card, from the cache when HEAD, the index, and the root files are unchanged."""
    out = git("rev-parse", "--show-toplevel", "--absolute-git-dir", "HEAD", cwd=repo_dir).stdout.split("\n")
    if len(out) < 3 or not out[0]:
        return "Repo card: not a git repo. Read the repo docs."
    top, git_dir = Path(out[0]), Path(out[1])
    stamps = [out[2]]
    for path in (git_dir / "index", top / ".github" / "workflows", *(top / n for n in ROOT_FILES)):
        try:
            stat = path.stat()
            stamps.append(f"{path}:{stat.st_mtime_ns}:{stat.st_size}")
        except OSError:
            stamps.append(f"{path}:-")
    key = hashlib.sha1("\n".join(stamps).encode()).hexdigest()
    cache = CARD_DIR / f"{hashlib.sha1(str(top).encode()).hexdigest()[:16]}.json"
    try:
        cached = json.loads(cache.read_text())
        if cached["key"] == key:
            return cached["text"]
    except (OSError, ValueError, KeyError, TypeError):
        pass
    text = build_card(top)
    try:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"key": key, "text": text}))
    except OSError:
        pass
    return text


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
    sig.add_argument("--posted", type=int, help="accept: the count of findings posted")
    sig.add_argument("--dropped", type=int, help="accept: the count of drafted findings not posted")
    sig.add_argument("--repo-dir", default=".")
    les = sub.add_parser("lessons", parents=[common])
    les.add_argument("--repo-dir", default=".")
    rep = sub.add_parser("report", parents=[common])
    rep.add_argument("--repo-dir", default=".")
    step0 = sub.add_parser("step0", parents=[common])
    step0.add_argument("--repo-dir", default=".")
    syn = sub.add_parser("sync", parents=[common])
    syn.add_argument("direction", choices=["pull", "push"])
    args = parser.parse_args()
    if args.action == "signal" and args.kind == "accept" and (args.posted is None or args.dropped is None):
        sig.error("accept needs --posted N and --dropped N: the counts of findings posted and not posted")
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
    elif args.action == "report":
        report(root, args.repo_dir)
    elif args.action == "step0":
        print(repo_card(args.repo_dir))
        lessons(root, args.repo_dir)
    else:
        sync(root, args.direction)


if __name__ == "__main__":
    main()
