# Learning: consolidate and revert

`<shepherd>` is the folder this file is in; `<clone>` is `<shepherd>/../..`.
Learning runs only from a full clone: if `<clone>/setup/claude-md.md` doesn't
exist, say so and stop.

| Path under `<shepherd>` | Holds | Shared |
|---|---|---|
| `lessons/global.md` | lessons for every repo, written only here | pushed with the public clone |
| `lessons/repos/<slug>.md` | one repo's lessons, written at runtime | its own local git repo; pushed only to a remote the user adds |
| `inbox/signals.jsonl` | every recorded correction, with evidence | never |
| `inbox/turns.jsonl` | prompts and replies from sessions that ran shepherd, last 30 days | never |

## Consolidate: "consolidate shepherd lessons"

Only when the user asks.

1. Read the date in `inbox/last-consolidation` (missing: read everything),
   the signals and turns since then, `lessons/global.md`, and every
   `lessons/repos/*.md`.
2. Find corrections that were never recorded: user turns that reject a
   finding, undo a cut, or ask for a check back, with no matching signal.
3. Propose, each with its evidence (signal count, repos, dates):
   - Promote: a lesson seen in 2 or more repos moves to `global.md`, or, when
     it changes a rule, into the `code/` or `lang/` file that owns the rule.
   - Narrow: a rule rejected 3 or more times gets narrower wording or a named
     exception in its file.
   - Drop: duplicate lessons, and lessons the core rules now cover.
   - Record: each correction from step 2, through `capture.py signal`.
4. List every signal flagged `never-cut`. Never apply one, and never propose a
   change that weakens the never-cut list in `code/defensive.md`.
5. Caps: `global.md` 30 lines, each `code/` and `lang/` file 150 lines, each
   repo file 40 lines. At a cap, merge or drop before adding.
6. `global.md` and the core files are public. Write them generically: no repo,
   company, person, path, or code from the evidence.
7. Show the full diff and apply it only on a yes.
8. Commit public files in `<clone>` and repo files in `lessons/repos/`, each
   as `lesson(consolidate): <summary>`, and `git push -q` where a remote
   exists. Then write today's date (`YYYY-MM-DD`) to `inbox/last-consolidation`.

## Revert: "revert shepherd <commit>"

1. Find the commit with `git -C <clone> show --stat <commit>`, else
   `git -C <shepherd>/lessons/repos show --stat <commit>`.
2. Show it and say what reverting undoes. On a yes, run
   `git revert --no-edit <commit>` in that repo, then `git push -q` where a
   remote exists.

## Sync repo lessons across machines

Only when the user asks. Create a private repo, then run
`git -C <shepherd>/lessons/repos remote add origin <url>` and
`git -C <shepherd>/lessons/repos push -u origin HEAD`. From then on, each
lesson is pushed in the background and pulled at most hourly, fast-forward
only. If two machines diverge, syncing stops until someone runs
`git -C <shepherd>/lessons/repos pull --rebase` and resolves the conflicts.
