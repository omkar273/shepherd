# Write mode

## 1. Map before writing code

- Trace the path that the change touches: entry point, handler, service,
  store or external call, and response. Read the path. Do not infer it.
- Write the reach list: every place that the change must reach.
  - Callers of anything whose signature or behavior changes.
  - Registrations: routes, router tables, DI containers, worker or job setup,
    exports and barrel files.
  - Error-to-status mappings for every new error value.
  - Config and env, including the example env file.
  - Migrations, and generated code. Regenerate that code. Never edit it by
    hand.
  - Tests, only where the repo's test policy asks for them.
- Pick the rung from the ladder in `SKILL.md`.
- Before you call an API, read its signature in the source or in the
  installed version. Before you use a CLI flag, check `--help`.
- Fix a bug once, in the shared code, not in one caller.

## 2. The diff contract

The finished diff contains exactly these items:

1. The requested behavior. It must be correct when things fail. Some changes
   write more than one row, or move money or quantities. Make this type of
   change atomic and safe against two concurrent requests. Use one
   transaction, or a conditional update (`... where balance >= $1`). Use the
   mechanism that the code already has, or the smallest one inside the
   existing layer. Never add a new layer. Correctness is never a follow-up.
2. The wiring from the reach list.
3. Tests where the repo's test policy asks for them, or where the user asked
   for them.
4. Fixes for genuine bugs (wrong behavior) in code that the change touches.
   Name each fix under `Fixed alongside:` in the report.

Put nothing else in the diff. This rules out:

- Refactors of existing code.
- Helpers extracted from code that you only touched.
- "Improvements" to how existing paths behave.
- Hardening that neighbouring code does not have.
- Doc comments.
- The removal of old comments.

If one of these looks worth doing, leave it out. List it under `Follow-ups:`
in the report.

Add or remove checks by the rules in `code/defensive.md`.

Also, work like a lazy senior developer:

- Do not build features, options, or flexibility that nobody asked for. Name
  what you skipped in one line. For a vague request, build the smallest
  version that does the core job.
- Unless the repo's test policy says otherwise, add one small test or an
  assert-based self-check for new non-trivial logic. Non-trivial logic is a
  branch, a loop, a parser, money or security, or a whole new script. Trivial
  changes need none.
- For a shortcut with a known limit, write
  `shortcut: <the limit>, <when to upgrade>`.
- If options are equal in size, take the one that is correct on edge cases. A
  one-liner that the reader must decode is not short.

### Levels

The default level is full. The user can say "lite" or "ultra". The user can
also say "normal mode" to turn off all of this. The choice stays for the rest
of the session.

| Level | Behavior |
|---|---|
| lite | Build what the user asked for. Name the smaller option in one line. Let the user pick. |
| full | Follow the rules above. |
| ultra | Also question the request. Before you build, push back on any part that the need does not justify. |

## 3. Self-check before saying done

1. If the diff adds more than 20 lines, do the refine pass. A prompt does
   not make a diff smaller. A separate pass after the diff exists does.
   - Start one subagent on the cheapest model (`model: "haiku"`). Do not
     fork it. A fork gets all of your context and your model.
   - Give it the prompt below. Fill in the request, the repo path, and the
     path of this skill.
   - Apply each cut that it returns. Do not apply a cut that removes wiring
     from the reach list or an item on the never-cut list in
     `code/defensive.md`. Report each cut that you do not apply.
   - Do one pass only.

   ```text
   Refine pass. Do not edit files.
   Request: <the user's request>
   Repo: <repo path>. The diff is `git diff <base>` plus the new files that
   `git status --short` lists. <base> is the commit before the task.
   Read the "Shared cut list" section of <shepherd>/SKILL.md, section 2 of
   <shepherd>/code/write.md, and <shepherd>/code/defensive.md.
   For each hunk, name the part of the request or the contract item (1 to 4)
   that it serves. Return only the hunks to revert or to make smaller. For
   each one, give file:line, the cut-list item or "serves nothing", and the
   new text or "delete". The behavior for valid inputs must not change.
   Never cut an item on the never-cut list, wiring, a test that the repo's
   policy asks for, or a bug fix. If no hunk fails, return "none".
   ```
2. Confirm each item on the reach list. Grep every new exported symbol to
   prove that other code calls or registers it.
3. Run the repo's own checks after your last edit: lint, typecheck or build,
   and focused tests. Use the scripts that the repo defines. Never append
   `|| true`.
4. Write the report in this format:

```text
Rung: <ladder rung, and why, in one line>
Changed: <file - what, one line each>
Lean: -<N> lines cut in the refine pass (or: nothing cut)
Fixed alongside: <adjacent bug - fix, one line each, or none>
Follow-ups: <deliberately left out, or none>
Not checked: <what could not be verified, or none>
```

If setup installed the write hooks (`context.md`), a lint hook shows the
findings for each file that you edit. A Stop hook blocks the stop one time
until steps 1, 3, and 4 are done.
