# Learning: record, consolidate, and revert

`<shepherd>` is the folder that contains this file. `<clone>` is
`<shepherd>/../..`. Learning runs only from a full clone. If
`<clone>/setup/claude-md.md` does not exist, say so and stop.

| Path under `<shepherd>` | Holds | Shared |
|---|---|---|
| `lessons/global.md` | the lessons for every repo, written only here | pushed with the public clone |
| `lessons/repos/<slug>.md` | the lessons for one repo, written at runtime, and an `## Archive` section | its own local git repo, pushed only to a remote that the user adds |
| `inbox/signals.jsonl` | each recorded correction and accepted review, with its evidence | never |
| `inbox/turns.jsonl` | the user prompts and replies from sessions that ran shepherd in the last 30 days | never |

The `turn` hook removes machine text from a prompt before it logs the prompt.
Machine text is a `[SYSTEM NOTIFICATION` block, a task notification, a system
reminder, or a message from another agent. Only the words of the user stay.

## Record a correction

If the user corrects your work, record the correction before you reply. Run
this command from inside the repo:
`python3 <shepherd>/hooks/capture.py signal --kind <kind> --rule "<shepherd rule>" --evidence "<file:line> <one-line paraphrase>"`

- `reject`: the user rejects or edits a finding before you post it. Or the
  user says that you kept or cut a check, abstraction, or file by mistake.
- `revert`: the user reverts a cut.
- `restore`: you put back a removed check because a test failed.
- `accept`: the user tells you to post a review. Add `--posted N --dropped N`:
  the count of findings that you posted and the count that you dropped. The
  evidence names these findings.

Do not put secrets or code in the evidence. If a reject, revert, or restore is
clear and specific to the repo, add `--lesson "<what to do in this repo, and why>"`.
To count a lesson again, pass its exact text. If the lesson makes the
never-cut list weaker, add `--flag never-cut` instead. Then tell the user that
the lesson does not apply.

Show the user all of the script output. If the output has a full lessons
file, show that file too.

## Lesson life cycle

Each repo lesson is one line:
`- <lesson>. (conf 0.6, seen 1x, added <date>, used <date>, cite <file:line>)`

- `cite`: the first word of the evidence, if it is a file in the repo. A
  lesson with no file in its evidence has no citation.
- `conf`: the confidence. A `reject` starts at 0.6, a `revert` at 0.7, and a
  `restore` at 0.8. Each new record of the lesson adds 0.1, to a limit of 1.0.
- `seen`: the count of records.
- `used`: the last date that `capture.py lessons` showed the lesson to a
  session, or that a signal recorded it again.

`capture.py lessons` applies these rules:

1. It shows no lesson whose cited file or line is gone.
2. It shows at most 8 repo lessons. It ranks them by confidence, then by the
   used date.
3. It moves a lesson to `## Archive` when its used date is more than 60 days
   older than the newest used date in the file. A repo that nobody opens
   keeps its lessons. The archive is not shown, and the script deletes
   nothing.
4. A lesson that a signal records again comes back from the archive.

A line in the old format, `- <lesson>. (<date>, seen Nx)`, gets the new
format at the next write. Its date becomes the added date and the used date.

## Shepherd or auto memory

Claude Code auto memory (`~/.claude/projects/<project>/memory/`) also keeps
facts for a repo. Do not keep one fact in both places. A lesson stays in
shepherd only if one of these conditions is true:

- It changes how a shepherd rule applies in this repo: what to cut or keep,
  which findings to raise, or what Step 0 must check.
- It must be on each machine of the user. Only the lessons repo syncs. Auto
  memory stays on one machine.

Other facts go to auto memory: workflow choices (merge style, approval steps,
speed), facts about the user, and project state. For these, record the signal
without `--lesson`. If `signal` or `report` names a similar auto memory note,
tell the user. Then propose to drop one of the two copies.

## Propose a check

If a lesson is seen 3 or more times and a tool can check it, propose a check.
A tool can check a lesson that names a command, a file, a pattern, or a value.
`signal` and `report` name these lessons.

1. Write a lint rule in the linter config of the repo, if the linter can
   express the lesson. Else, write a Claude Code hook in the
   `.claude/settings.json` of the repo.
2. Show the user the diff and the lesson that it replaces.
3. Apply the diff only after the user says yes. Then move the lesson to the
   archive, because the check now does its job.

## Consolidate: "consolidate shepherd lessons"

Do this only when the user asks.

1. Run `python3 <shepherd>/hooks/capture.py report` from inside the repo. It
   counts the signals since the date in `inbox/last-consolidation`. It shows
   the review precision: the posted findings divided by the drafted findings.
   It also names the rules with 3 or more rejects, the never-cut flags, the
   check proposals, the stale citations, and the auto memory duplicates.
   Show the user the report. Then read the turns since that date, `lessons/global.md`,
   and every `lessons/repos/*.md`, with its archive.
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
   - Drop: drop duplicate lessons, and lessons that the core rules, a lint
     rule, a hook, or auto memory now cover.
   - Cite: give a lesson with a stale citation a new `file:line`, or drop it.
   - Restore: move an archived lesson back if the user still wants it.
   - Check: propose each check from the report (Propose a check).
   - Record: record each correction from step 2 with `capture.py signal`.
4. List every signal with the `never-cut` flag. Never apply one of these
   signals. Never propose a change that weakens the never-cut list in
   `code/defensive.md`.
5. Keep each file within its line cap:
   - `global.md`: 30 lines.
   - Each `code/` and `lang/` file: 150 lines.
   - Each repo file: 40 lessons above `## Archive`.

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
