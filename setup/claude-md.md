## Shepherd

For any code change, PR review, plan, or debugging, and for any skills task,
use the `shepherd` skill first.

- Repo `CLAUDE.md`/`AGENTS.md` and lint rules win over generic advice.
- Take the first rung that holds: not needed, already in the repo, stdlib,
  existing dependency, minimal new code.
- Wire it fully: callers, registrations, exports, config. Grep to prove new
  code is reachable.
- A check stays only if it guards a trust boundary or a case you can name.
  Never cut auth, tenant scoping, money invariants, or cleanup.
- Before "done": reread the diff, cut the excess, run the repo's checks.
- Commits and PR bodies: never a model name, never a `Co-Authored-By:` or
  "Generated with" trailer.
