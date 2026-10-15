#!/usr/bin/env python3
"""Check markdown prose against the ASD-STE100 rules in ste.md that a script
can see: sentence and paragraph length, semicolons, contractions, perfect and
progressive verbs, and words that have a plain replacement.

With no files, checks the prose this repo authors: each .md file in a skill
with `origin: mine` (not README.md or lessons/), AGENTS.md, and
setup/claude-md.md. Pass - to check stdin, for example a commit message.
Skips code, tables, headings, and HTML comments. Skips quoted text for the
word and verb checks. Exits 1 on a finding."""
import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import skill_meta

REPO = Path(__file__).resolve().parents[3]
MAX_WORDS = 25
MAX_SENTENCES = 6
PLAIN = {
    "utilize": "use", "utilise": "use", "commence": "start", "ensure": "make sure",
    "prior to": "before", "in order to": "to", "leverage": "use", "facilitate": "help",
}
NOT_VERBS = {"thing", "things", "nothing", "something", "anything", "everything", "string",
             "strings", "during", "ceiling", "setting", "settings", "warning", "warnings"}
CHECKS = [
    ("semicolon", re.compile(r";")),
    ("contraction", re.compile(r"\b\w+n['’]t\b|\b\w+['’](re|ve|ll|d)\b|\b(i['’]m|it['’]s|let['’]s)\b", re.I)),
    ("perfect", re.compile(r"\b(has|have|had)\s+(\w+ed|been|done|gone|run|written|seen|made|taken|given|found|left|got|gotten)\b", re.I)),
    ("progressive", re.compile(r"\b(am|is|are|was|were|be|been|being)\s+(\w{3,}ing)\b", re.I)),
    ("plain word", re.compile(r"\b(" + "|".join(PLAIN) + r")\b", re.I)),
]
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(])")
LIST_ITEM = re.compile(r"^\s*([-*+]|\d+\.)\s+")


def authored_files():
    files = [REPO / "AGENTS.md", REPO / "setup" / "claude-md.md"]
    for skill in sorted((REPO / "skills").iterdir()):
        if (skill / "SKILL.md").exists() and skill_meta.read_origin(skill).get("origin") == "mine":
            files += sorted(p for p in skill.rglob("*.md")
                            if p.name != "README.md" and "lessons" not in p.relative_to(skill).parts)
    return files


def blocks(text):
    """Yield (line, is_list_item, text) for each prose paragraph and list item."""
    lines = text.splitlines()
    start = 0
    if lines and lines[0] == "---" and "---" in lines[1:]:
        start = lines.index("---", 1) + 1
        description = skill_meta.parse_frontmatter("\n".join(lines[1:start - 1])).get("description")
        if description:
            line = next(n for n, l in enumerate(lines, 1) if l.startswith("description:"))
            yield line, False, description
    cur, first, is_item, fenced = [], 0, False, False
    for n, line in enumerate(lines[start:], start + 1):
        s = line.strip()
        if s.startswith("```"):
            fenced = not fenced
        skip = fenced or s.startswith(("```", "#", "|", "<!--"))
        if skip or not s or LIST_ITEM.match(line):
            if cur:
                yield first, is_item, " ".join(cur)
            cur, is_item = [], bool(LIST_ITEM.match(line)) and not skip
            if is_item:
                cur, first = [LIST_ITEM.sub("", line).strip()], n
            continue
        if not cur:
            first = n
        cur.append(s)
    if cur:
        yield first, is_item, " ".join(cur)


def lint(text):
    """Return (line, message) for each rule that the text breaks."""
    findings = []
    for n, is_item, block in blocks(text):
        block = re.sub(r"`[^`]*`", "CODE", block)
        block = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", block)
        sentences = [s for s in SENTENCE_END.split(block) if s.strip()]
        for sentence in sentences:
            words = sum(1 for w in sentence.split() if re.search(r"\w", w))
            if words > MAX_WORDS:
                findings.append((n, f"long sentence ({words} words > {MAX_WORDS}): {sentence[:80]}"))
        if not is_item and len(sentences) > MAX_SENTENCES:
            findings.append((n, f"long paragraph ({len(sentences)} sentences > {MAX_SENTENCES})"))
        unquoted = re.sub(r"\"[^\"]*\"|“[^”]*”", "QUOTE", block)
        for rule, rx in CHECKS:
            for m in rx.finditer(unquoted):
                if rule == "progressive" and m.group(2).lower() in NOT_VERBS:
                    continue
                hint = f", use \"{PLAIN[m.group(0).lower()]}\"" if rule == "plain word" else ""
                findings.append((n, f"{rule}: \"{m.group(0)}\"{hint}"))
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", help="markdown files, or - for stdin")
    args = parser.parse_args()
    paths = args.files or authored_files()
    findings = []
    for path in paths:
        text = sys.stdin.read() if path == "-" else Path(path).read_text()
        label = path if path == "-" else os.path.relpath(path)
        findings += [f"{label}:{n}: {message}" for n, message in lint(text)]
    print("\n".join(findings) or f"{len(paths)} files, no STE findings.")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
