# shepherd evals

Synthetic repos with planted problems and traps. They show whether a change to
`shepherd` helps or hurts before it ships. Nothing here is loaded when the
skill runs.

## Fixtures

| Fixture | What it is | Branch under review |
|---|---|---|
| `go-billing` | Go service: invoices, a repository scoped by tenant, handlers, a worker | `feat/void-invoices` |
| `ts-app` | TS rpc app with zod, Svelte and React | `feat/apply-credit` |
| `ts-app-v2` | `ts-app` plus a nested `AGENTS.md`, legacy comments, a side-effect import, and a store bug | none (write task) |

Build one as a real git repo:

```bash
bash evals/build_fixture.sh go-billing /tmp/eval-go
```

`answer-key.md` lists every planted issue (the agent should catch it) and
every trap (the agent must not remove it). Agents under test never see it.

## Scenarios

Run each one in a fresh agent session, with nothing else in the prompt. Then
score the output against `answer-key.md`.

1. **Go review:**
   "A teammate opened a PR and asked me for a review. Please review it and
   draft the review comments you would leave on the PR. Do not post anything
   anywhere and do not modify the repo. Repo: `<dir>`. The PR is the branch
   `feat/void-invoices`, targeting `main`. Give me the draft review, then a
   section "Files read" listing every file you opened."
2. **TS review:** the same prompt on `ts-app`, branch `feat/apply-credit`.
3. **TS write:**
   "In `<dir>` (ts-app-v2), add an rpc procedure `applyCredit` that lets the
   signed-in customer apply part of their credit balance to one of their
   unpaid invoices. It should reduce the customer's credit balance and record
   the credit on the invoice. Also show the amount due in the invoice total
   component in `web/`. Commit your work, then summarize, then list every file
   you opened."

## Scoring

- **Caught:** planted issues found, out of the total in the key.
- **Traps cut:** trap checks the agent recommends removing. Must be 0.
- **Triggered:** the "Files read" list includes `shepherd` files. A run that
  doesn't load the skill isn't measuring it.
- **Write runs:** diff size, plus every V-item in the key.

## Results so far

| Date | Version | Go review | TS review | Traps cut | Notes |
|---|---|---|---|---|---|
| 2026-10-11 | no skill | 11/12 | 14/15 | 1 | Baseline. Recommended removing the tenant re-check |
| 2026-10-11 | lean (predecessor) | 12/12 | 15/15 | 0 | Write diffs −60% (Go 310→125, TS 132→59) |
| 2026-10-12 | shepherd, first description | n/a | n/a | 1 | Did not trigger in 5/5 runs; lost reviews to the built-in code-review skill |
| 2026-10-12 | shepherd, fixed description | 12/12 | 15/15 | 0 | Triggered in all runs; routing loaded only matching language files |

## Adding a case

1. Add the code to `fixtures/<name>/base/`, and the change under review as
   `pr.patch` (`git format-patch --stdout main..<branch>`).
2. Teach `build_fixture.sh` the branch name.
3. Add the planted issues and traps to `answer-key.md`.
4. Add it to `CASES` in `skills/shepherd/scripts/tests/test_evals.py`.
