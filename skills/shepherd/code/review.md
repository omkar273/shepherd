# Review mode

Use review mode for a teammate's pull request or branch. Do not check out
or switch a branch. Do not change the working tree.

## Run the lenses in agents

Do these steps first, before you read code:

1. Find the target: a PR number, or a branch and its base.
2. Spawn the `shepherd:reviewer` agent. Give it only the target as the
   prompt: `42`, or `feat/x main`. It runs the lenses in parallel agents on a
   lower-cost model. It returns findings with a confidence score.
3. Go to "Merge". Do not read the diff, the changed files, or the `lang/`
   files in this session. The lenses read them.

Spawn the agent even if you already read the diff. Do not do the lenses
yourself when the agent is available. Its parallel lenses find more, and its
confidence scores let the merge drop false findings.

Run the lenses yourself only if `shepherd:reviewer` is not in your agent
list, or if it fails. Then gather the context as in the next section. Read
`agents/reviewer.md` and `agents/lens.md`, and do each lens in turn. In those
files, `${CLAUDE_PLUGIN_ROOT}` is the shepherd folder.

## Gather, without touching the working tree

Do this only when you run the lenses yourself.

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

## Merge

You merge the findings. Do not review the code again.

1. Drop each finding with a confidence under 80. Count the drops.
2. Drop each finding that removes or weakens an item on the never-cut list
   in `code/defensive.md`.
3. Drop each guideline finding with no `Rule:` quote. If a quote is not in a
   file that you read, check all such quotes with one `git grep -F` call at
   the head. Drop each finding whose quote is not there.
4. If two findings name the same root cause, keep one. Keep the best
   evidence and the higher group.
5. If one lens says to cut a check and a different lens says to keep it, keep
   the check. Drop the cut finding.
6. If a MUST finding has thin evidence, check it with one `git show` or
   `git grep` call. If the check fails, drop the finding.
7. Put each finding that is left in a group of the draft. Use the group that
   the lens gave, unless the table in "Draft for the user" puts it in a
   different group.

## Finding contract

Each finding is: `file:line`, what it is, evidence, fix.

- Evidence is concrete: the callers that you grepped, the invariant, where
  the duplicate is, the repo rule that the change breaks.
- A guideline finding quotes the rule word for word, with the path of the
  doc.
- The fix deletes, inlines, moves, or wires code.
- A concern is not a lean finding if its fix adds new code (a shared helper,
  a feature, hardening, tests beyond what the repo requires). Give it one
  line under `Outside lean`, or drop it. Add a pointer to `/code-review` or
  `/security-review` for depth.
- A `shortcut:` or TODO comment that names its limit is the author's decision,
  not a finding.
- For issues that the repo's linter catches, say "lint will flag these" once.

## Draft for the user

Show the draft in chat. Never post it on your own.

```text
Verdict: comment | request changes   Lean: -<N> lines
Not checked: <...>   Dropped: <N> under confidence 80

MUST    broken wiring, a removed never-cut check, a wrong result, behavior the PR breaks
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
