# Audit and debt ledger

Use this file for "audit this repo", "review like the one who gets paged",
"what can I delete", and "list the shortcuts". The output is a report that the
user asked for. Give it in full. Do not change anything. For a teammate's PR,
`code/review.md` owns the process and the format. Its lenses in
`agents/lens.md` use the categories below: `wiring` uses bug, scale, speed,
and missing test, `defensive` uses risk, and `cut` uses lean.

The order of importance is: correct, safe, holds under load, tested, fast,
lean.

## 1. Map first

- Audit what the user names (a folder, a package, a change). If the user
  names nothing, audit the whole repo, or the uncommitted changes for a
  change review.
- Read the README, the deploy and build config, the dependency list, the entry
  points, and the tests. For a change, also read the callers of every changed
  function.
- Find the expected load (one person who runs a script, or many users and
  processes). Say which load you assumed.
- Trace the main flows end to end: input, storage, output. Read in the most
  detail where a mistake costs the most (user input, money, auth, writes,
  jobs, shared state). Say which parts you did not read.

## 2. Look for

1. Bug: a wrong result, a crash, or a missed edge case (empty, zero, last
   item, rounding, time zones). Also look for a fix in one caller while the
   shared function stays broken.
2. Risk: injection, weak randomness, secrets in code, or unchecked user input.
   Also look for swallowed errors, writes in the wrong order, or a missing
   transaction.
3. Scale: check-then-write races, the same work in every process, state that
   only grows, or a query per item. Also look for O(n^2) on big input, or
   per-process state that must be shared.
4. Missing test: risky logic (branch, parser, money, security, writes) with no
   test that fails when it breaks. The fix is one good test, not coverage.
5. Speed: big slowdowns are findings. Small wins are suggestions.
6. Lean: code that matches the shared cut list in `SKILL.md`. Write each fix
   as one of these: delete, reuse (name the path), stdlib or native, yagni,
   merge, or split. Split by job, never by line count.

## 3. Before you report

- Every finding names a concrete case: this input leads to this wrong result.
  If you cannot name a case, do not report a finding. Do not report style
  taste. Do not write "consider".
- Before you call code dead, run the "Proving code is unused" checks.
- A `shortcut:` comment that names its limit is a decision, not a finding,
  unless the load already crosses that limit.
- Give the smallest fix that works. Prefer fixes that delete code.

## 4. Output

Rank the findings. Give each finding one line: `file:line`, plain-English
problem, case, fix. End with the assumed load and `Not checked:`.

## Debt ledger

List every deliberate shortcut so a deferral cannot quietly become permanent.

- Scan with `git grep --no-index --exclude-standard -nE '(#|//|/[*]|--|<!--) ?shortcut:'`.
  If the user names another marker word, scan for that word. If the stack
  needs other comment prefixes, add them. Skip hits that are not a deferral.
- Group the rows by file. Write one row for each marker in this format:
  `<file>:<line>, <what was simplified>. ceiling: <limit>. upgrade: <trigger>.`
- Tag a marker that names no upgrade trigger `no-trigger`.
- End with `<N> markers, <M> with no trigger.`, or `No shortcut debt.`
- Write the ledger to a file only when the user asks for a file.
