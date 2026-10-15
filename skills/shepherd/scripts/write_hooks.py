#!/usr/bin/env python3
"""Claude Code hooks that hold write mode to code/write.md.

stop: Stop. If the turn wrote a file in the git repo (any tool: the file's
      mtime is after the prompt), blocks the stop until the repo's checks ran
      after the last write. It blocks once: the next stop in a row always
      goes through.
lint: PostToolUse on Edit|Write|MultiEdit. Runs the linter that the repo
      configures for the edited file and returns only its findings, the
      findings on the edited lines first.

Each reads the hook's JSON on stdin. On any error it prints nothing and exits
0, so a broken hook never blocks or changes a session."""
import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

WRITE_MD = Path(__file__).resolve().parent.parent / "code" / "write.md"
SCRIPT_CHECKS = ("lint", "typecheck", "type-check", "check", "test")
LOCKFILES = (("pnpm-lock.yaml", "pnpm"), ("yarn.lock", "yarn"), ("bun.lock", "bun"), ("bun.lockb", "bun"))
JS_SUFFIXES = {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".svelte", ".vue"}
TRANSCRIPT_TAIL_BYTES = 4 * 1024 * 1024
LINT_TIMEOUT = 30
MAX_FINDINGS = 20


def git(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=10)


def git_root(folder):
    out = git(folder, "rev-parse", "--show-toplevel")
    return Path(out.stdout.strip()).resolve() if out.returncode == 0 else None


def seconds(timestamp):
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00")).timestamp()


def turn(transcript, prompt_id):
    """The prompt's timestamp, and the main thread's (time, tool, input) calls since then."""
    with open(transcript, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - TRANSCRIPT_TAIL_BYTES))
        lines = f.read().splitlines()
    entries = []
    for line in lines:
        try:
            entry = json.loads(line)
        except ValueError:
            continue
        if isinstance(entry, dict) and not entry.get("isSidechain"):
            entries.append(entry)
    users = [i for i, e in enumerate(entries) if e.get("type") == "user"]
    # Older versions do not send prompt_id: the prompt is then the last user text.
    start = ([i for i in users if entries[i].get("promptId") == prompt_id][:1]
             or [i for i in users if isinstance((entries[i].get("message") or {}).get("content"), str)][-1:])[0]
    calls = []
    for entry in entries[start + 1:]:
        content = (entry.get("message") or {}).get("content")
        if entry.get("type") != "assistant" or not isinstance(content, list):
            continue
        calls += [(seconds(entry["timestamp"]), block.get("name"), block.get("input") or {})
                  for block in content if block.get("type") == "tool_use"]
    return seconds(entries[start]["timestamp"]), calls


def written(root, prompt_time):
    """{file: mtime} of the repo files that the turn wrote, with any tool."""
    base = git(root, "rev-list", "-1", f"--before=@{int(prompt_time)}", "HEAD").stdout.strip()
    listed = git(root, "diff", "--name-only", "-z", base) if base else git(root, "ls-files", "-z")
    names = set(listed.stdout.split("\0") + git(root, "ls-files", "-z", "--others", "--exclude-standard")
                .stdout.split("\0")) - {""}
    files = {name: (root / name).stat().st_mtime for name in names if (root / name).is_file()}
    return {name: mtime for name, mtime in files.items() if mtime >= prompt_time}


def repo_checks(root):
    """(command to show, pattern that a run of it matches) for each check the repo defines."""
    checks = []
    package = root / "package.json"
    if package.is_file():
        scripts = json.loads(package.read_text()).get("scripts") or {}
        runner = next((tool for lock, tool in LOCKFILES if (root / lock).exists()), "npm")
        checks += [(f"{runner} run {name}", re.compile(rf"\b(npm|pnpm|yarn|bun)\b.*\b{name}\b"))
                   for name in SCRIPT_CHECKS if name in scripts]
    makefile = root / "Makefile"
    if makefile.is_file():
        targets = set(re.findall(r"^([\w-]+)\s*:", makefile.read_text(), re.M))
        checks += [(f"make {name}", re.compile(rf"\bmake\b.*\b{name}\b"))
                   for name in SCRIPT_CHECKS if name in targets]
    if (root / "go.mod").is_file():
        checks.append(("go vet ./...", re.compile(r"\bgo vet\b|\bgolangci-lint\b")))
    if (root / "Cargo.toml").is_file():
        checks.append(("cargo check", re.compile(r"\bcargo (check|clippy|build|test)\b")))
    if has_ruff_config(root):
        checks.append(("ruff check .", re.compile(r"\bruff\b")))
    return checks


def stop(data):
    if data.get("stop_hook_active"):
        return None
    root = git_root(data["cwd"])
    checks = repo_checks(root) if root else []
    if not checks:
        return None
    prompt_time, calls = turn(Path(data["transcript_path"]), data.get("prompt_id"))
    files = written(root, prompt_time)
    if not files:
        return None
    last = max(files.values())
    ran = [args.get("command") or "" for when, name, args in calls if name == "Bash" and when >= last]
    missing = [shown for shown, pattern in checks if not any(pattern.search(c) for c in ran)]
    if not missing:
        return None
    return {"decision": "block", "reason": (
        f"Run the repo's checks after your last edit (step 4 of section 3 in {WRITE_MD}): "
        f"{', '.join(missing)}. Fix what they find. If a check cannot run, name it under Not checked.")}


def has_ruff_config(folder):
    pyproject = folder / "pyproject.toml"
    return ((folder / "ruff.toml").is_file() or (folder / ".ruff.toml").is_file()
            or (pyproject.is_file() and "[tool.ruff" in pyproject.read_text()))


def nearest(path, root, has):
    """The closest folder from the file's folder up to root that passes has(), else None."""
    for folder in path.parents:
        if has(folder):
            return folder
        if folder == root:
            return None
    return None


def plain(out):
    return out.stdout + "\n" + out.stderr


def eslint_text(out):
    """ESLint 9 has no line formatter, so read its JSON."""
    return "\n".join(f"{Path(f['filePath']).name}:{m['line']}:{m.get('column', 0)}: "
                     f"{m['message']} ({m.get('ruleId')})"
                     for f in json.loads(out.stdout or "[]") for m in f["messages"] if m.get("line"))


def drop_type_errors(out):
    """go vet marks a type error with "vet: ". Mid-change it is noise, and the build check finds it."""
    return "\n".join(line for line in plain(out).splitlines() if not line.startswith("vet: "))


def linter(path, root):
    """(name, folder to run in, argv, output to text) for the repo's linter of path, else None."""
    if path.suffix in (".py", ".pyi"):
        folder = nearest(path, root, has_ruff_config)
        if folder and shutil.which("ruff"):
            return "ruff", folder, ["ruff", "check", "--output-format", "concise", "--quiet", str(path)], plain
    if path.suffix in JS_SUFFIXES:
        folder = nearest(path, root, lambda f: any(f.glob("eslint.config.*")) or any(f.glob(".eslintrc*")))
        bins = [d / "node_modules" / ".bin" / "eslint" for d in (folder, root)] if folder else []
        eslint = next((b for b in bins if b.is_file()), None)
        if eslint:
            return "eslint", folder, [str(eslint), "--format", "json", str(path)], eslint_text
    if path.suffix == ".go":
        if nearest(path, root, lambda f: any(f.glob(".golangci.*"))) and shutil.which("golangci-lint"):
            return "golangci-lint", path.parent, ["golangci-lint", "run", "."], plain
        if shutil.which("go"):
            return "go vet", path.parent, ["go", "vet", "."], drop_type_errors
    return None


def edited_lines(response):
    """Line numbers that the edit wrote in the new file, or None for the whole file."""
    if response.get("type") == "create" or "structuredPatch" not in response:
        return None
    lines = set()
    for hunk in response["structuredPatch"]:
        number = hunk["newStart"]
        for text in hunk["lines"]:
            if text.startswith("+"):
                lines.add(number)
            if not text.startswith("-"):
                number += 1
    return lines


def lint(data):
    path = Path(data["tool_input"]["file_path"]).resolve()
    root = git_root(path.parent)
    found = linter(path, root) if root and path.is_file() else None
    if found is None:
        return None
    name, folder, argv, to_text = found
    out = subprocess.run(argv, cwd=folder, capture_output=True, text=True, timeout=LINT_TIMEOUT)
    finding = re.compile(rf"(?:^|[\s/]){re.escape(path.name)}:(\d+):")
    findings = [(int(m[1]), line.strip()) for line in to_text(out).splitlines()
                if (m := finding.search(line))]
    if not findings:
        return None
    edited = edited_lines(data["tool_response"])
    inside = [text for number, text in findings if edited is None or number in edited]
    outside = [text for number, text in findings if edited is not None and number not in edited]
    lines = [f"{name} findings in {path.name} after this edit:"] + inside
    if outside:
        lines += ["Outside the edited lines (fix only the ones that this edit caused):"] + outside
    if len(lines) > MAX_FINDINGS:
        lines = lines[:MAX_FINDINGS] + [f"({len(lines) - MAX_FINDINGS} more lines)"]
    return {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "\n".join(lines)}}


HOOKS = {"stop": stop, "lint": lint}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("hook", choices=HOOKS)
    args = parser.parse_args()
    try:
        result = HOOKS[args.hook](json.load(sys.stdin))
    except Exception:
        return
    if result is not None:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
