# Review mode

Use review mode for a teammate's pull request or branch.

## Gather, without touching the working tree

- For a GitHub PR:
  - Run `gh pr view <n> --json title,body,baseRefName,headRefOid,files,url`.
  - Run `gh pr diff <n>`.
  - Run `git fetch origin pull/<n>/head`.
  - Read files at the head SHA with `git show <sha>:<path>`. Grep with
    `git grep -n <pattern> <sha>`.
  - Never run `gh pr checkout`. Never switch branches.
- For a local branch, run `git diff <base>...<branch>`. Then run the same
  `git show` and `git grep` commands at the branch tip.
- At that revision, read the repo's root `CLAUDE.md` / `AGENTS.md`. At the
  same revision, read every `AGENTS.md` on the path down to each directory
  that the diff touches. Load the `lang/` files that match the file
  extensions in the diff.
- The PR's intent is its title, body, and linked issue. Judge the scope
  against this intent.

## Passes, in order

1. Wiring. For each changed signature or behavior, grep every caller at the
   head. Check every reach-list item that the change implies:
   - registrations (routes, DI, workers, router tables, exports)
   - error-to-status mappings for new error values
   - config and env
   - migrations
   - generated code
   - any construction site that the repo's docs list
2. Defensive checks. Review each defensive check by the tiers in
   `code/defensive.md`. Keep never-cut items out of the findings.
3. The shared cut list in `SKILL.md`. If the PR deletes code as unused, run
   the "Proving code is unused" checks. If the PR deletes something
   load-bearing, report it as a MUST.
4. Scope. Find hunks that are unrelated to the PR's intent. These include old
   comments or lint backlog that the PR strips from files that it only
   touches.

## Finding contract

Each finding is: `file:line`, what it is, evidence, fix.

- Evidence is concrete: the callers that you grepped, the invariant, where
  the duplicate is, the repo rule that the change breaks.
- The fix deletes, inlines, moves, or wires code.
- A concern is not a lean finding if its fix adds new code (a shared helper,
  a feature, hardening, tests beyond what the repo requires). Give it one
  line under `Outside lean`, or drop it. Put correctness and security bugs
  that you notice by chance under `Outside lean` too. Add a pointer to
  `/code-review` or `/security-review` for depth.
- A `shortcut:` or TODO comment that names its limit is the author's decision,
  not a finding.
- For issues that the repo's linter catches, say "lint will flag these" once.

## Draft for the user

Show the draft in chat. Never post it on your own.

```text
Verdict: comment | request changes   Lean: -<N> lines   Not checked: <...>

MUST    broken wiring, a removed never-cut check, behavior the PR breaks
SHOULD  HIGH-tier checks, cut-list abstractions, out-of-scope hunks
ASK     MEDIUM-tier checks, phrased as a question
Outside lean    one line each
```

Number the findings across all groups. Give each pure deletion a GitHub
`suggestion` block, so that the author can apply it in one click. If the repo
has its own review format, map MUST and SHOULD to its "act on" level. In that
case, map ASK to the "consider" level of that format.

## Posting, only after the user approves

- The user picks the findings to post. The user can also edit them.
- Post one review with the event `COMMENT` and only the approved inline
  comments. Write the payload to a temporary file outside the repo. Then run
  `gh api repos/{owner}/{repo}/pulls/<n>/reviews --method POST --input <file>`:

```json
{
  "commit_id": "<head sha>",
  "event": "COMMENT",
  "body": "<summary>",
  "comments": [{ "path": "src/a.ts", "line": 42, "side": "RIGHT", "body": "<finding>" }]
}
```

- Never use `APPROVE` or `REQUEST_CHANGES` unless the user asks for that
  event. Never push, commit, or resolve threads.
- If a PR has more than about 40 files or 1,500 changed lines, review it
  stack by stack. List the areas that you skip under `Not checked:`.
