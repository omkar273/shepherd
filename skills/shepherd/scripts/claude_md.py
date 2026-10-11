#!/usr/bin/env python3
"""Write setup/claude-md.md into ~/.claude/CLAUDE.md between managed markers.

An existing managed block is replaced; everything outside it is kept
byte for byte. Without a block, one is appended."""
import argparse
from pathlib import Path

BLOCK_FILE = Path(__file__).resolve().parents[3] / "setup" / "claude-md.md"
BEGIN = "<!-- skills:begin -->"
END = "<!-- skills:end -->"


def render(existing, block):
    section = f"{BEGIN}\n{block}{END}"
    if existing is None:
        return f"{section}\n"
    if BEGIN in existing and END in existing:
        before, rest = existing.split(BEGIN, 1)
        _, after = rest.split(END, 1)
        return f"{before}{section}{after}"
    separator = "" if existing.endswith("\n") else "\n"
    return f"{existing}{separator}\n{section}\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--home", default=str(Path.home()))
    args = parser.parse_args()
    path = Path(args.home).expanduser() / ".claude" / "CLAUDE.md"
    existing = path.read_text() if path.exists() else None
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(existing, BLOCK_FILE.read_text()))


if __name__ == "__main__":
    main()
