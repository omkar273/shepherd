# Learning: consolidate and revert

`<shepherd>` is the folder that contains this file. `<clone>` is
`<shepherd>/../..`. Learning runs only from a full clone. If
`<clone>/setup/claude-md.md` does not exist, say so and stop.

| Path under `<shepherd>` | Holds | Shared |
|---|---|---|
| `lessons/global.md` | the lessons for every repo, written only here | pushed with the public clone |
| `lessons/repos/<slug>.md` | the lessons for one repo, written at runtime | its own local git repo, pushed only to a remote that the user adds |
| `inbox/signals.jsonl` | each recorded correction, with its evidence | never |
| `inbox/turns.jsonl` | the prompts and replies from sessions that ran shepherd in the last 30 days | never |

## Consolidate: "consolidate shepherd lessons"

Do this only when the user asks.

1. Read the date in `inbox/last-consolidation`. Read the signals and turns
   since that date. If there is no date, read all of them. Also read
   `lessons/global.md` and every `lessons/repos/*.md`.
2. Find the unrecorded corrections. An unrecorded correction is a user turn
   that has no matching signal and that:
   - rejects a finding,
   - undoes a cut, or
   - asks for a check back.
3. Propose these changes. Show the evidence for each change: the signal
   count, the repos, and the dates.
   - Promote: move a lesson that occurs in 2 or more repos to `global.md`. If
     the lesson changes a rule, move it into the `code/` or `lang/` file that
     owns the rule instead.
   - Narrow: if a rule has 3 or more rejections, give it narrower wording or a
     named exception in its file.
   - Drop: drop duplicate lessons, and lessons that the core rules now cover.
   - Record: record each correction from step 2 with `capture.py signal`.
4. List every signal with the `never-cut` flag. Never apply one of these
   signals. Never propose a change that weakens the never-cut list in
   `code/defensive.md`.
5. Keep each file within its line cap:
   - `global.md`: 30 lines.
   - Each `code/` and `lang/` file: 150 lines.
   - Each repo file: 40 lines.

   If a file is at its cap, merge or drop content before you add content.
6. `global.md` and the core files are public. Write them in general terms. Do
   not put a repo, company, person, path, or code from the evidence in them.
7. Show the full diff. Apply it only after the user says yes.
8. Commit the public files in `<clone>` and the repo files in
   `lessons/repos/`. Give each commit the message
   `lesson(consolidate): <summary>`. If a repo has a remote, run `git push -q`
   in it. Then write today's date (`YYYY-MM-DD`) to `inbox/last-consolidation`.

## Revert: "revert shepherd <commit>"

1. Find the commit with `git -C <clone> show --stat <commit>`. If that command
   does not find it, use
   `git -C <shepherd>/lessons/repos show --stat <commit>`.
2. Show the commit. Say what the revert undoes. If the user says yes, run
   `git revert --no-edit <commit>` in that repo. Then, if the repo has a
   remote, run `git push -q`.

## Sync repo lessons across machines

Do this only when the user asks. Create a private repo. Then run
`git -C <shepherd>/lessons/repos remote add origin <url>` and
`git -C <shepherd>/lessons/repos push -u origin HEAD`. After that, shepherd
pushes each lesson in the background. It pulls at most once an hour, and only
as a fast-forward. If two machines diverge, the sync stops until someone runs
`git -C <shepherd>/lessons/repos pull --rebase` and resolves the conflicts.
