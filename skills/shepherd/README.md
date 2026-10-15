# shepherd

**Cut the bloat. Keep the checks.**

shepherd is a skill that makes your coding agent write the smallest change that
works, and stops it from deleting the checks that matter. There is no command
to remember: ask for a feature, a fix, or a code review as usual, and shepherd
loads itself.

## What it does

- **Writing code:** before adding anything, it checks whether the change is
  needed at all, then whether the repo, the standard library, or an existing
  dependency already does the job. It leaves out one-implementation interfaces,
  pass-through functions, flags nobody sets, and comments that restate the
  code.
- **Keeping checks:** it never removes authentication, tenant scoping, money
  invariants, state guards, rollback, or cleanup, even when another layer also
  checks.
- **Reviewing code:** it drafts review comments sorted into MUST, SHOULD, and
  ASK, and every suggested fix deletes, inlines, moves, or wires code.
- **Reporting:** each change ends with a short report of what changed, how many
  lines it cut, and what it couldn't verify.

In shepherd's own evals (2026-10-16, Sonnet), reviews with no skill told the
author to delete a never-cut check in 5 of 6 runs. With the full setup, 0 of 9
runs did, and reviews cost about 20% less than with the skill alone. The evals
and how to rerun them are in the
[repository](https://github.com/omkar273/shepherd).

## What it runs and sends

shepherd is instructions for the agent and one local script. When the skill
loads, it runs `hooks/capture.py step0`. The script reads your repository's
config files (`package.json` scripts, Makefile, CI workflows, lint config),
lists nested `AGENTS.md` files, and prints them with the repository's lessons.
It caches that card in `~/.claude/shepherd/repo-cards/`. Claude Code may ask
once before it runs the skill, because the skill pre-approves this script.

In a full clone, two hooks log the prompts and replies of sessions that use
shepherd to the clone's `inbox/`, and the script pulls the clone at most once an
hour. shepherd has no MCP servers. While it works, the agent:

- reads files in your repository and runs your repository's own checks, such
  as its linter and tests;
- runs read-only git commands such as `git diff` and `git log`;
- posts a pull-request review with `gh` only after you approve the draft.

The `scripts/` folder holds the setup and update tools for the full setup from
the repository. They link skills into `~/.claude/skills` and the language
rules into `~/.claude/rules/shepherd`, and add a block to `~/.claude/CLAUDE.md`.
They can add a session-start reminder and context hooks to
`~/.claude/settings.json`, and fetch optional skill packs from GitHub, each
only after you say yes. When shepherd is installed as a plugin, it doesn't run
them.

## License

MIT. See the [repository](https://github.com/omkar273/shepherd).
