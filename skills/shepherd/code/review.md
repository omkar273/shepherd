# Review mode

For a teammate's pull request or branch.

## Gather, without touching the working tree

- GitHub PR:
  - `gh pr view <n> --json title,body,baseRefName,headRefOid,files,url`
  - `gh pr diff <n>`
  - `git fetch origin pull/<n>/head`
  - Read and grep at the head SHA: `git show <sha>:<path>`,
    `git grep -n <pattern> <sha>`.
  - Never run `gh pr checkout` and never switch branches.
- Local branch: `git diff <base>...<branch>`, then the same `git show` and
  `git grep` at the branch tip.
- Read the repo's root `CLAUDE.md` / `AGENTS.md` at that revision, plus every
  `AGENTS.md` on the path down to each directory the diff touches. Load
  `lang/` files by the diff's file extensions.
- The PR's intent is its title, body, and linked issue. Judge scope against
  that.

## Passes, in order

1. Wiring. For each changed signature or behavior, grep every caller at the
   head. Check every reach-list item the change implies: registrations
   (routes, DI, workers, router tables, exports), error-to-status mappings
   for new error values, config and env, migrations, generated code, and any
   construction site the repo's docs list.
2. Defensive checks, by the tiers in `code/defensive.md`. Never-cut items stay
   out of the findings.
3. The shared cut list in `SKILL.md`. Where the PR deletes code as unused,
   run the "Proving code is unused" checks; deleting something load-bearing
   is a MUST.
4. Scope: hunks unrelated to the PR's intent, including old comments or lint
   backlog stripped from files the PR only touches.

