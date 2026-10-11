# Write mode

## 1. Map before writing code

- Trace the path the change touches: entry point, handler, service,
  store or external call, response. Read it; don't infer it.
- Write the reach list: every place the change must land.
  - Callers of anything whose signature or behavior changes.
  - Registrations: routes, router tables, DI containers, worker or job setup,
    exports and barrel files.
  - Error-to-status mappings for every new error value.
  - Config and env, including the example env file.
  - Migrations, and generated code (regenerate it, never hand-edit it).
  - Tests, only where the repo's test policy asks for them.
- Pick the rung from the ladder in `SKILL.md`.
- Before calling an API, read its signature in the source or in the installed
  version. Before using a CLI flag, check `--help`.
- Fix a bug once, in the shared code, not in one caller.

## 2. The diff contract

The finished diff contains exactly:

1. The requested behavior, correct when things fail. When the change writes
   more than one row, or moves money or quantities, it is atomic and safe
   against two concurrent requests: one transaction, or a conditional update
   (`... where balance >= $1`). Use the mechanism the code already has, or
   the smallest one inside the existing layer; never a new layer. Correctness
   is never a follow-up.
2. The wiring from the reach list.
3. Tests where the repo's test policy asks for them, or the user asked.
4. Fixes for genuine bugs (wrong behavior) in code the change touches, each
   one named under `Fixed alongside:` in the report.

Nothing else goes in. That rules out refactors of existing code, extracting
helpers from code you only touched, "improvements" to how existing paths
behave, hardening that neighbouring code doesn't have, doc comments, and
stripping old comments. If one of those looks worth doing, leave it out and
list it under `Follow-ups:` in the report.

Add or remove checks per `code/defensive.md`.

## 3. Self-check before saying done

1. Run `git diff` and read it as one design. For each hunk, name the contract
   item (1 to 4) it serves. Revert every hunk that serves none.
2. Walk the shared cut list over every added function, type, and file. Inline
   or delete whatever fails it.
3. Tick off the reach list. Grep every new exported symbol to prove it is
   called or registered.
4. Run the repo's own checks: lint, typecheck or build, focused tests, using
   the scripts the repo defines. Never append `|| true`.
5. Report in this shape:

```text
Rung: <ladder rung, and why, in one line>
Changed: <file - what, one line each>
Lean: -<N> lines cut in self-check (or: nothing cut)
Fixed alongside: <adjacent bug - fix, one line each, or none>
Follow-ups: <deliberately left out, or none>
Not checked: <what could not be verified, or none>
```
