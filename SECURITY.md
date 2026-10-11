# Security policy

## What is in scope

Setup changes files in your home directory, so these matter most:

- `link_skills.py` creates symlinks in `~/.claude/skills` and
  `~/.agents/skills` and moves existing entries to `~/.skills-backup`.
- `claude_md.py` rewrites a marked block in `~/.claude/CLAUDE.md`.
- `settings.py` edits `~/.claude/settings.json` and can add a hook that runs at
  every session start.
- `sync_skill.py` copies files from the sources recorded in `.origin.yaml`.

A vulnerability is anything that makes these scripts delete or overwrite data
outside the backup folder, run code that the user did not approve, write
outside the documented paths, or pull untrusted content into a skill without
it being visible in the diff.

## Supported versions

Only the latest commit on `main` is supported.

## Reporting a vulnerability

Do not open a public issue. Report it privately through
[GitHub's private vulnerability reporting](https://github.com/omkar273/shepherd/security/advisories/new),
with the steps to reproduce and the files affected.

You can expect an acknowledgement within 7 days and a fix or a decision within
30 days. You will be credited in the fix unless you ask not to be.
