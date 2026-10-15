## Shepherd

Use the `shepherd` skill first for each code change, PR review, plan, debug
session, and skills task.

- Repo `CLAUDE.md`/`AGENTS.md` and lint rules win over generic advice.
- Use the first rung that holds: not needed, already in the repo, stdlib, a
  dependency that the repo has, minimal new code.
- Wire it fully: callers, registrations, exports, config. Use grep to prove
  that new code is reachable.
- Keep a check only if it guards a trust boundary or a case that you can
  name. Never cut auth, tenant scoping, money invariants, or cleanup.
- Before you say "done", do these steps: read the diff again, cut the excess,
  and run the repo's checks.
- Write prose in ASD-STE100 Simplified Technical English: docs, comments,
  commit messages, PR bodies, and reviews. The shepherd file `ste.md` has the
  rules.
- Do not put a model name, a `Co-Authored-By:` trailer, or a "Generated with"
  trailer in a commit or a PR body.

## Compact Instructions

When you compact, keep the goal, the decisions, the changed files, the
commands that ran, the current failure, and the next step. Drop tool output
that you already used.
