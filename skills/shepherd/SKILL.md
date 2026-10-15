---
name: shepherd
description: Use when you start a task that writes, changes, deletes, tests, reviews, or debugs code or docs in a repo, before the first tool call. That includes a feature, a fix, a refactor, a failing test, a review of a pull request, branch, or diff, and a multi-file plan. Use it before you remove a field, function, or check that looks dead or duplicate, and before you say a change is done. Use it before you add a helper, wrapper, interface, layer, option, defensive check, or test that the task did not ask for. With the shepherd card in CLAUDE.md, use it only for an audit, a multi-file plan, a user correction, SEO work, or a long session. Always use it to set up, update, add, prune, or check skills.
allowed-tools: Bash(python3 "${CLAUDE_SKILL_DIR}/hooks/capture.py" *)
hooks:
  UserPromptSubmit:
    - hooks:
        - type: command
          command: 'python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/shepherd}/hooks/capture.py" turn || true'
  Stop:
    - hooks:
        - type: command
          command: 'python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/shepherd}/hooks/capture.py" turn || true'
---

# Shepherd

Make the smallest change that does the job, and wire it into the code that is
already there. Cut before you add. Repo rules win over this skill.

## Step 0, every time

```!
python3 "${CLAUDE_SKILL_DIR}/hooks/capture.py" step0 || true
```

1. The block above is the repo card and the lessons. Do what the lessons say.
   If it shows no repo card, run `python3 <shepherd>/hooks/capture.py step0`
   from the repo (`<shepherd>` is the folder of this skill).
2. Claude Code loads the root `CLAUDE.md` or `AGENTS.md`. Do not read it
   again. Read the other files in one parallel batch with the code. These
   are each nested `AGENTS.md` or `CLAUDE.md` from the card on the path to the
   change, and the files from the route. Do not use a turn only for shepherd
   files.
3. The order of priority is: repo docs, recorded decisions (ADRs,
   architecture notes), the never-cut list, the lessons, then this skill. Do
   not flag what a recorded decision justifies. Add a new package or module
   boundary only when the user or a recorded decision asks for it.
4. Docs go out of date. Before you use a file, helper, or mechanism that a doc
   names, make sure that it is in the code.
5. If the repo has its own build or review skill or workflow (for example
   `.agents/skills/review`), follow its process and report format. Run
   shepherd's checks inside it.

## Route

This file covers an ordinary change, fix, or removal. Read another shepherd
file only when a row below applies.

| Situation | Read or use |
|---|---|
| Reviewing a PR or branch | `code/review.md`, `code/defensive.md` |
| Auditing a repo or a change (bugs, risk, scale, tests, bloat), or listing deferred shortcuts | `code/audit.md` |
| The user asks for "lite" or "ultra" mode, or for the full write report | `code/write.md` |
| `.go` files or `go.mod` | + `lang/go.md` |
| `.ts` files | + `lang/typescript.md` |
| `.svelte`, `.svelte.ts` | + `lang/typescript.md`, `lang/svelte.md` |
| `.tsx`, `.jsx`, React imports | + `lang/typescript.md`, `lang/react.md` |
| Planning a multi-file or unclear change | the superpowers `brainstorming` skill, then `writing-plans`. If the repo uses Matt's issue flow, suggest `/to-spec` to the user. Only the user can start it. |
| A bug or a failing test | the superpowers `systematic-debugging` skill |
| About to say a change is done | the superpowers `verification-before-completion` skill |
| No skill in the listing fits the task | the descriptions of the name-only skills from the SessionStart hook. If one fits, call it by name. Read only that skill. |
| "Set up", "update", "add" or "status" for skills | `skills.md` |
| Installing or removing a pack, or a task that fits a pack: planning, productivity, design, reverse engineering, video, writing, SEO, simulation | `skills.md`, Packs |
| Adding or removing a catalog skill | `curate.md` |
| SEO or AEO work on a site or product | `seo.md` |
| A long, slow, or messy session | `context.md` |
| The user corrects your work | `learn.md`, Record a correction. Do this before you reply. |
| "Consolidate shepherd lessons", "revert shepherd <commit>" | `learn.md` |

If a superpowers skill above is not installed, do its step yourself:

- Before an edit to many files, decide the goal and write a short plan.
- Before a fix, find the root cause.
- Before you say done, run the checks and read their output.

Read only the `lang/` files that match the change, before the first line in
that language. Setup installs them as path rules, so a `lang/` file can
already be in context. Then do not read it again. If a language has no file,
use the repo's own docs. Do not make up rules for a language.

## The ladder

Use the first rung that holds, and name it in one line:

1. Not needed: say so and stop.
2. Already in the repo: reuse it in the same way as the code around it.
   Extend the service or module that is there. Do not add a parallel one.
3. The standard library or platform.
4. A dependency that the repo already has.
5. Minimal new code.

## Write

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

## Never cut

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

## Shared cut list

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

A comment earns its place only for a non-obvious why or an outside constraint
(a library bug, a spec, an audit item). Write a known shortcut as
`shortcut: <the limit>, <when to upgrade>`. Delete commented-out code.

## Proving code is unused

Grep does not find every reference. Before you call code unused, also check
side-effect imports (`import "./x"`), string-keyed registration (routes, DI
names, event names), config globs and paths, reflection, and tests. If a
removal can break something with no error, keep the code.

## Always on

- Run the repo's linter. Do not restate the rules that it enforces. In a
  review, a broken documented convention is a finding. Quote the doc.
- Write all prose in ASD-STE100 Simplified Technical English (STE): docs,
  comments, commit messages, PR bodies, findings, and reports. Use short
  sentences, the active voice, one word for each meaning, and no contractions
  or semicolons. Read `ste.md` before you write a doc or a skill file.
- Use Read to view source and Grep to search it, in parallel batches. Do not
  read a file again just after you edit it.
- Read a web page as text first. Take a screenshot only for a visual check, at
  scale 0.5 or less. Convert a PDF to text with `pdftotext`.
