## Shepherd

These rules apply to each code change and review. Repo rules win over them.
Claude Code loads the root `CLAUDE.md` or `AGENTS.md`. Before the first edit,
read each nested `AGENTS.md` or `CLAUDE.md` on the path to a changed file, and
the lint config. Read the files that are not in context in one parallel batch.

Do not load the `shepherd` skill for an ordinary change or review. This card
covers them. Load the skill for an audit, a multi-file plan, SEO work, a long
session, or a skills task (set up, update, add, prune, status). When the user
corrects your work, load it before you reply.

### Ladder

Use the first rung that holds, and name it. The rungs are: not needed, already
in the repo, the standard library, a dependency that the repo has, and minimal
new code. If the repo has the code, extend it. Do not add a parallel module.

### Write

Before you write, read the path that the change touches: the entry point,
handler, service, store, and response. Read each function that the new code
calls, and make sure that it does what its name says. Fix a bug once, in the
shared code, not in one caller.

The diff contains only these items:

1. The requested behavior, correct when things fail. If the change writes
   more than one row or moves money or quantities, make it atomic and safe
   against two concurrent requests. Do it inside the existing layer:
   - If the store has a transaction API, use one transaction.
   - If the store has no transaction API, use a conditional update. Put the
     guard and the arithmetic in the statement
     (`set balance = balance - $1 where id = $2 and balance >= $1`). If no
     row changes, the guard failed.
   - Do not read a value, compute the new value in code, and write it back.
     Do not defer the race as a limitation or a follow-up.
2. The wiring: callers, registrations (routes, router tables, DI, workers,
   exports), an error-to-status mapping for each new error, config and env,
   migrations, and generated code.
3. Tests where the repo's test policy asks for them.
4. Fixes for real bugs (wrong behavior) in the files that the change edits or
   calls. This includes a function that the new code does not use. Name each
   fix under `Fixed alongside:` in your report.

Put nothing else in the diff. That excludes refactors, extracted helpers, and
hardening that the neighbouring code does not have. It also excludes doc
comments and the removal of old comments. List these items under
`Follow-ups:`. Before you say done, read `git diff` and revert each hunk that
serves no item. Grep each new export to prove a caller, and run the repo's
checks.

### Cut list

- An interface with one implementation. Exception: a repo convention or a test
  fake needs it. Grep before you flag it.
- A factory, manager, registry, or options layer with one consumer.
- A function that only forwards to one call. A one-expression helper with one
  or two callers that names no domain concept. An error factory. A catch that
  only throws again.
- An option or flag that every caller leaves at its default. A stub that only
  logs "would do X". A generic type parameter that one type fills. An alias
  that only renames.
- Near-duplicates merged behind a boolean flag. Keep the copies.
- A comment that only restates the code below it. Logging on the happy path.
- Validation again after a boundary schema. A nil or undefined guard on a
  value that a type or a constructor guarantees.
- Edits outside the task: refactors, renames, and formatting.

### Never cut

Keep these checks, even when another layer also checks:

- Authentication, authorization, and ownership checks.
- Tenant, environment, and org scoping, in queries and as re-checks in
  services. A second scoping check is defense in depth, not duplication.
- Money and quantity invariants. State-machine guards (already paid, already
  voided). Idempotency guards.
- Rollback, `defer`, `finally`, and locks. Timeouts and retries around network
  I/O.
- Error translation that callers use. A check that a comment explains or a
  test asserts.

When you move or merge code, keep its checks. In a review, keep these checks
out of the findings. Do not tell the author to remove, merge, or weaken one,
also not for consistency with other code. Before you remove any other check,
write its invariant and grep every caller.

The user can tell you to remove one of these checks because it is dead or a
duplicate. Do not remove it immediately. First grep every path to the code,
also workers, jobs, and tests. If a path does not go through the other check,
the claim is false: keep the check and name that path. If the claim is true,
name the never-cut item and the invariant that the check keeps, and ask one
time. Remove the check only after the user confirms.

### Review

Do not change the working tree. Use `git diff main...<branch>` and
`git show <sha>:<path>`. Do four passes: wiring, defensive checks, the cut
list, and scope against the intent of the PR. Each finding has `file:line`,
the problem, the evidence, and a fix that deletes, inlines, moves, or wires
code. The evidence is the callers that you grepped and the rule that the code
breaks. Put each finding in one group:

- MUST: broken wiring, a removed never-cut check, broken behavior.
- SHOULD: cut-list items, redundant checks, out-of-scope hunks.
- ASK: a swallow-and-default (`?? 0`, `return nil`) on data that can really be
  absent. Write it as a question.
- Outside lean: one line for each idea that adds code.

Show the draft. Post it only after the user approves it.

### Always

- Read files with the Read tool, in one parallel batch. Make changes with Edit
  and Write. Do not read or change files through the shell (`cat`, `sed`, or a
  script). Edit needs a Read first, and a shell edit can stop for approval.
- Write prose in ASD-STE100 Simplified Technical English: docs, comments,
  commit messages, PR bodies, and reviews. The shepherd file `ste.md` has the
  rules.
- Do not put a model name, a `Co-Authored-By:` trailer, or a "Generated with"
  trailer in a commit or a PR body.

## Compact Instructions

When you compact, keep the goal, the decisions, the changed files, the
commands that ran, the current failure, and the next step. Drop tool output
that you already used.
