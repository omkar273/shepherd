# Context hygiene

Every model becomes worse as its context grows, not only slower. Keep context
small on purpose. Content that never lands in context costs nothing later.

## One task per session

- Use a fresh session for each new, unrelated task. Before you switch
  sessions, write a handoff for the user to paste. Include the goal, the
  decisions, the changed files, the commands that prove that the change works,
  and the next step.
- After two failed corrections on the same problem, stop. Write the handoff
  with what you learned. Then suggest a fresh session.
- When the user is about to step away from a large session, suggest a
  handoff. A large session that the user resumes later re-sends all of its
  context.

## Compact at task boundaries

When a sub-task is complete and the session continues, suggest
`/compact <focus>`. In `<focus>`, name the goal, the decisions, the changed
files, and the next step. Never compact in the middle of a debugging thread.

## Bound what lands in context

- git: use `git commit -q`, `git push -q`, `git diff --stat` before a full
  diff, and `git log --oneline -n 20`. Leave lockfiles out of diffs
  (`-- . ':!*.lock'`).
- Builds and tests: pipe the output through `| tail -n 40`, or write the log
  to a file and grep it.
- Search before you read: Grep for the symbol. Then Read only the range that
  you need. Read large files with an offset and a limit.
- If you already have the output of a command, do not run the command again.
  Reuse the output.

## Delegate sweeps

- If you need to read 10 or more files or answer 3 or more independent
  questions, send an Explore subagent. Ask it for a summary of at most 1,500
  words with `file:line` references.
- Send long test runs and log digging to a subagent too. Only the conclusion
  comes back.

## Hooks

Setup can install these context hooks. Each hook fails open and never
blocks a session.

- **Context warning:** past 40% of the context window, and again past 60%,
  the hook shows one line. The line suggests a fresh session or `/compact` at
  the next task boundary. Act on it.
- **Trimmed output:** Bash output over 200 lines comes back as its first 60
  and last 60 lines, plus `[N lines trimmed; full log: <path>]`. Grep the log.
  Do not run the command again. Add `# full` to the command only when you must
  read the whole output.
- **No dumps:** the hook denies a plain `cat` or `sed -n '1,$p'` of a text
  file over 300 lines. Use Read with an offset and a limit, or use `grep -n`
  and then `sed -n 'a,bp'`.

Setup can also install two write hooks (`scripts/write_hooks.py`). They hold
write mode to the Write rules in `SKILL.md`. Each one fails open.

- **Lint:** after each Edit or Write, the hook runs the linter that the repo
  configures for that file: ruff, ESLint, golangci-lint, or `go vet`. It shows
  only the findings, and the findings on the edited lines come first. It
  does not show a `go vet` type error, because the build check finds it.
  Fix the findings that your edit caused. Do not fix old findings in lines
  that the task does not touch.
- **Stop:** if the turn wrote a file in the git repo with any tool, the hook
  blocks the stop one time. It blocks until the repo's checks ran after the
  last write. A file that changed after the prompt counts. The hook finds
  the checks in `package.json` scripts, `Makefile` targets, `go.mod`,
  `Cargo.toml`, and the ruff config. If a check cannot run, name it under
  `Not checked:`. The next stop always goes through, so the hook cannot
  loop.

## Check the meter

`/context` shows what fills the context window. If skills or MCP tools unused
in this repo take a large share, offer "prune skills for this repo"
(`skills.md`).
