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

In shepherd's own evals, the same feature took 125 lines instead of 310 in Go
and 59 instead of 132 in TypeScript, and reviews caught 27 of 27 planted
problems instead of 25. The evals and how to rerun them are in the
[repository](https://github.com/omkar273/shepherd).

## What it runs and sends

shepherd is instructions for the agent, not a program. It has no hooks, no MCP
servers, and makes no network calls of its own. While it works, the agent:

- reads files in your repository and runs your repository's own checks, such
  as its linter and tests;
- runs read-only git commands such as `git diff` and `git log`;
- posts a pull-request review with `gh` only after you approve the draft.

The `scripts/` folder holds the setup and update tools for the full setup from
the repository. They link skills into `~/.claude/skills`, add a block to
`~/.claude/CLAUDE.md`, can add a session-start reminder and context hooks to
`~/.claude/settings.json`, and fetch optional skill packs from GitHub, each
only after you say yes. When shepherd is installed as a plugin, it doesn't run
them.

## License

MIT. See the [repository](https://github.com/omkar273/shepherd).
