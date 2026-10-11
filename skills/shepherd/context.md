# Context hygiene

Every model gets worse as its context grows, not only slower. Keep context
small on purpose: what never lands in context costs nothing later.

## One task per session

- A new, unrelated task gets a fresh session. Before switching, write a
  handoff for the user to paste: goal, decisions, files changed, the commands
  that prove it works, and the next step.
- After two failed corrections on the same problem, stop. Write the handoff
  with what you learned and suggest a fresh session.
- When the user is about to step away from a large session, suggest a handoff:
  resuming a big session later re-sends all of it.

## Compact at task boundaries

When a sub-task is finished and the session continues, suggest
`/compact <focus>`, naming the goal, decisions, files changed, and the next
step. Never compact in the middle of a debugging thread.

## Bound what lands in context

- git: `git commit -q`, `git push -q`, `git diff --stat` before a full diff,
  `git log --oneline -n 20`. Leave lockfiles out of diffs (`-- . ':!*.lock'`).
- Builds and tests: pipe through `| tail -n 40`, or write the log to a file
  and grep it.
- Search before reading: Grep for the symbol, then Read only the range you
  need. Read large files with an offset and limit.
- Re-running a command whose output you already have adds nothing; reuse it.

## Delegate sweeps

- Reading 10 or more files, or answering 3 or more independent questions:
  send an Explore subagent and ask for a summary of at most 1,500 words with
  `file:line` references.
- Long test runs and log digging go to a subagent too; only the conclusion
  comes back.

## Hooks

Setup can install these; each fails open and never blocks a session.

- **Context warning:** past 40% of the context window, and again past 60%,
  one line suggests a fresh session or `/compact` at the next task boundary.
  Act on it.
- **Trimmed output:** Bash output over 200 lines comes back as its first and
  last 60 lines plus `[N lines trimmed; full log: <path>]`. Grep the log
  rather than re-running the command. Add `# full` to the command only when
  the whole output must be read.
- **No dumps:** a plain `cat` or `sed -n '1,$p'` of a text file over 300 lines
  is denied. Use Read with an offset and limit, or `grep -n` then
  `sed -n 'a,bp'`.

## Check the meter

`/context` shows what fills the window. If skills or MCP tools unused in this
repo take a large share, offer "prune skills for this repo" (`skills.md`).
