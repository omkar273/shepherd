# Skills: setup, update, add, status

`<shepherd>` is the folder this file is in: `skills/shepherd` inside the clone,
or `~/.claude/skills/shepherd` once installed. `<repo>` is the clone's root.
Run scripts with `python3 <shepherd>/scripts/<script>`. Every script takes
`--home <dir>`; pass it only when told to (tests, trial runs).

Every flow below needs the clone. First run
`test -f <shepherd>/../../setup/claude-md.md`. If it fails, shepherd was
installed on its own (with `npx skills` or as a plugin): run no script from
this folder. Tell the user these flows come with the full setup in the README,
and for an update give them `npx skills update shepherd` or
`claude plugin update shepherd@shepherd`, whichever installed it. Then stop.

## Setup: "set up my skills"

1. Check `git --version` and `python3 --version`. If one is missing, report it
   and stop. If `jq --version` fails, say the `git-guardrails-claude-code`
   hook needs it, and continue.
2. Run `link_skills.py --dry-run --retire`. Show the user what will be linked,
   backed up (with the backup path), retired, and pruned. Continue on yes.
3. Run `link_skills.py --retire`.
4. CLAUDE.md:
   - If `~/.claude/CLAUDE.md` holds an old `## Lean code` block outside the
     `<!-- skills:begin -->` markers, show it and remove it on yes.
   - Run `claude_md.py`.
5. Superpowers: if `superpowers:brainstorming` is not in your available
   skills, on yes run `claude plugin marketplace add obra/superpowers-marketplace`
   and then `claude plugin install superpowers@superpowers-marketplace`.
6. Update nudge:
   - Run `settings.py add-hook --event SessionStart --command 'python3 "$HOME/.claude/skills/shepherd/scripts/nudge.py"'`
     and show the diff it prints.
   - On yes, run it again with `--write`.
7. Context hooks (`context.md` says what each does). For each row, run
   `settings.py add-hook` with these arguments, show the diff, and on yes run
   it again with `--write`:
   - `--event UserPromptSubmit --command 'python3 "$HOME/.claude/skills/shepherd/scripts/context_hooks.py" warn'`
   - `--event PostToolUse --matcher Bash --command 'python3 "$HOME/.claude/skills/shepherd/scripts/context_hooks.py" trim'`
   - `--event PreToolUse --matcher Bash --command 'python3 "$HOME/.claude/skills/shepherd/scripts/context_hooks.py" guard'`
8. Auto-compact: run `settings.py merge --json '{"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "70"}}'`,
   show the diff, and on yes run it again with `--write`. If
   `~/.claude/settings.json` still has `autoCompactWindow: 300000` from an
   earlier setup, show it and remove it on yes.
9. Status line: ask whether they want context % in the status line, and say
   the context warning learns the model's window size from it (without it,
   the warning assumes 200k). On yes,
   run `settings.py merge --json '{"statusLine": {"type": "command", "command": "python3 \"$HOME/.claude/skills/shepherd/scripts/context_hooks.py\" statusline"}}'`,
   show the diff, and on yes run it again with `--write`.
10. Run `state.py stamp --repo <repo>`.
11. Report `claude --version` and offer `claude update`.
12. List the links made and say: restart Claude Code to load the new skills.
    Offer "prune skills" for the repos they work in most.

## Update: "update my skills"

1. Run `git -C <repo> pull --rebase --autostash -q`.
2. Run `GIT_TERMINAL_PROMPT=0 git -C <repo> push --dry-run -q`. If it fails,
   the user can't push this clone: go to step 4. Their vendored updates arrive
   with the pull, and the clone stays a clean copy of upstream.
3. Sync vendored skills:
   - Run `sync_skill.py --all` and `gen_catalog.py`, then
     `git -C <repo> diff --stat -- skills README.md`. Summarize what changed
     in each skill.
   - On yes, commit the synced skills and the catalog as
     `chore: sync vendored skills`, then run `git -C <repo> push -q`.
   - On no, run `git -C <repo> checkout -- skills`, then `gen_catalog.py`.
4. Run `link_skills.py`, then `state.py stamp --repo <repo>`.

## Add: "add skill X"

- Yours: `new_skill.py <name> --origin mine`, then write its `SKILL.md`.
- Vendored: `new_skill.py <name> --origin vendored --source-repo <url>
  --source-path <path> --source-ref <sha> --seed-from <local checkout of path>`.
- Then run `link_skills.py` and `gen_catalog.py`, run the tests from
  `<repo>/AGENTS.md`, and commit.

## Status: "skills status"

Run `status.py`; add `--remote` to compare vendored skills with their sources.
Summarize:
- links that are missing, broken, or shadowed
- vendored skills that are behind their source
- uncommitted changes
- days since the last update

## Prune: "prune skills for this repo"

1. Run `status.py --catalog --repo <the repo>`. It reads that repo's last 30
   days of transcripts locally and reports names and counts only; never quote
   transcript text.
2. Show the `unused_skills` and `unused_plugins`, grouped by `kind`.
3. Propose, for `<the repo>/.claude/settings.local.json`:
   - `skillOverrides`: `"name-only"` for unused `user`, `project`, and
     `builtin` skills (the user can ask for `"off"` instead);
   - `enabledPlugins`: `false` for each unused plugin that has a `key`.
   Plugins without a `key` came with the desktop app: report them only.
   `skillOverrides` does not apply to plugin skills.
4. Run `settings.py merge --file <the repo>/.claude/settings.local.json
   --json '<the proposal>'`, show the diff, and on yes run it again with
   `--write`. Nothing is written without that yes.

## Packs: "install the <pack> pack", "remove a pack", "what packs are there"

- **List:** `catalog.py list` shows each pack, its skills, and whether it is
  installed.
- **Install:** say which skills the pack adds and wait for a yes. Then run
  `catalog.py install <pack>` and report what was linked and backed up. If a
  new skill doesn't show up in the session, say: restart Claude Code to load
  it.
- **Remove:** `catalog.py uninstall <pack>` removes only the pack's links.
- **Clean the cache:** only when asked, `catalog.py prune`.
- **Add or remove a catalog skill:** follow `curate.md`.
