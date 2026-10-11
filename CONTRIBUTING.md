# Contributing

Thanks for helping. This repo is one skill to rely on, `shepherd`, plus the
skills it routes to. Small, focused changes are the easiest to accept.

## How the repo is laid out

- `skills/<name>/` holds one skill per folder. Each has a `SKILL.md` and an
  `.origin.yaml` that says whether it is authored here (`origin: mine`) or
  vendored from another repo (`origin: vendored`, with its source and commit).
- `skills/shepherd/` is the router. Its `SKILL.md` stays under 5,000 tokens
  (about 20,000 characters); details live in its section files.
- `skills/shepherd/scripts/` holds the setup and maintenance scripts. They use
  the Python 3 standard library only.

## Making a change

- **Vendored skills are never edited by hand.** To refresh one, run
  `python3 skills/shepherd/scripts/sync_skill.py <name>`. To change its
  behavior, contribute upstream.
- **New skill:** `python3 skills/shepherd/scripts/new_skill.py <name> --origin mine`
  (or `--origin vendored` with `--source-repo`, `--source-path`,
  `--source-ref` and `--seed-from`).
- **After adding or removing a skill:** regenerate the README catalog with
  `python3 skills/shepherd/scripts/gen_catalog.py`.
- **Scripts:** add a failing test in `skills/shepherd/scripts/tests/` first,
  then the code. Every script takes `--home <dir>`; tests must use a temporary
  home and never touch the real `~/.claude`.

## Before opening a pull request

```bash
python3 -m unittest discover -s skills/shepherd/scripts/tests
```

All tests pass, including the repo checks (skill names match folders,
vendored skills record their source, the catalog is current, the router is
within budget).

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): subject`, imperative and lower case, for example
`feat(shepherd): add a status summary line`. One logical change per commit.

Commit messages and pull request descriptions never name an AI model and never
carry a `Co-Authored-By:` or "Generated with" trailer.
