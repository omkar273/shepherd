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

