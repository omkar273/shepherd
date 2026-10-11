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

## Finding contract

Each finding is: `file:line`, what it is, evidence, fix.

- Evidence is concrete: the callers grepped, the invariant, where the
  duplicate lives, the repo rule it breaks.
- The fix deletes, inlines, moves, or wires code.
- A concern whose fix adds new code (a shared helper, a feature, hardening,
  tests beyond what the repo requires) is not a lean finding. Give it one line
  under `Outside lean`, or drop it. Correctness and security bugs you happen
  to notice go there too, with a pointer to `/code-review` or
  `/security-review` for depth.
- A `shortcut:` or TODO comment that names its limit is the author's decision,
  not a finding.
- Issues the repo's linter catches: say "lint will flag these" once.

## Draft for the user

Show the draft in chat. Never post it on your own.

```text
Verdict: comment | request changes   Lean: -<N> lines   Not checked: <...>

MUST    broken wiring, a removed never-cut check, behavior the PR breaks
SHOULD  HIGH-tier checks, cut-list abstractions, out-of-scope hunks
ASK     MEDIUM-tier checks, phrased as a question
Outside lean    one line each
```

Number findings across all groups. Pure deletions get a GitHub
`suggestion` block so the author can apply them in one click. If the repo has
its own review format, map MUST and SHOULD to its "act on" level and ASK to its
"consider" level.

## Posting, only after the user approves

- The user picks which findings go out, and may edit them.
- Post one review with event `COMMENT` and only the approved inline comments.
  Write the payload to a temp file outside the repo, then run
  `gh api repos/{owner}/{repo}/pulls/<n>/reviews --method POST --input <file>`:

```json
{
  "commit_id": "<head sha>",
  "event": "COMMENT",
  "body": "<summary>",
  "comments": [{ "path": "src/a.ts", "line": 42, "side": "RIGHT", "body": "<finding>" }]
}
```

- Never use `APPROVE` or `REQUEST_CHANGES` unless the user says to. Never push,
  commit, or resolve threads.
- Large PRs (over about 40 files or 1,500 changed lines): review stack by
  stack, and list skipped areas under `Not checked:`.
