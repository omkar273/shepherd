# Audit and debt ledger

For "audit this repo", "review like the one who gets paged", "what can I
delete", and "list the shortcuts". A report the user asked for: give it in
full, change nothing. For a teammate's PR, `code/review.md` owns the process
and format; use the six categories below as its extra lenses.

Order of importance: correct, safe, holds under load, tested, fast, lean.

## 1. Map first

- Audit what the user names (a folder, a package, a change); nothing named
  means the whole repo, or the uncommitted changes for a change review.
- Read the README, deploy and build config, dependency list, entry points,
  and tests. For a change, also read the callers of every changed function.
- Find the expected load (one person running a script, or many users and
  processes) and say which you assumed.
- Trace the main flows end to end: input, storage, output. Go deep where a
  mistake costs most (user input, money, auth, writes, jobs, shared state).
  Say which parts you did not read.

## 2. Look for

1. Bug: wrong result, crash, missed edge case (empty, zero, last item,
   rounding, time zones), a fix applied in one caller while the shared
   function stays broken.
2. Risk: injection, weak randomness, secrets in code, unchecked user input;
   swallowed errors, writes in the wrong order, no transaction.
3. Scale: check-then-write races, the same work in every process, state that
   only grows, a query per item, O(n^2) on big input, per-process state that
   must be shared.
4. Missing test: risky logic (branch, parser, money, security, writes) with
   no test that fails when it breaks. One good test, not coverage.
5. Speed: big slowdowns are findings; small wins are suggestions.
6. Lean: the shared cut list in `SKILL.md`, as delete, reuse (name the path),
   stdlib or native, yagni, merge, or split (by job, never by line count).

## 3. Before you report

- Every finding names a concrete case: this input leads to this wrong result.
  No case, no finding. No style taste, no "consider".
- Run the "Proving code is unused" checks before calling code dead.
- A `shortcut:` comment that names its limit is a decision, not a finding,
  unless the load already crosses that limit.
- The fix is the smallest that works; prefer fixes that delete code.

## 4. Output

Ranked, each finding one line: `file:line`, plain-English problem, case, fix.
End with the load assumed and `Not checked:`.

## Debt ledger

List every deliberate shortcut so a deferral cannot quietly become permanent.

- Scan: `git grep --no-index --exclude-standard -nE '(#|//|/[*]|--|<!--) ?shortcut:'`
  (the user may name another marker word; add other comment prefixes if the
  stack needs them). Skip hits that are not a deferral.
- One row per marker, grouped by file:
  `<file>:<line>, <what was simplified>. ceiling: <limit>. upgrade: <trigger>.`
- Tag a marker that names no upgrade trigger `no-trigger`.
- End with `<N> markers, <M> with no trigger.`, or `No shortcut debt.`
- Write the ledger to a file only when asked.
