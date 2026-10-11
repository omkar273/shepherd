# Skills: setup, update, add, status

`<shepherd>` is the folder this file is in: `skills/shepherd` inside the clone,
or `~/.claude/skills/shepherd` once installed. `<repo>` is the clone's root.
Run scripts with `python3 <shepherd>/scripts/<script>`. Every script takes
`--home <dir>`; pass it only when told to (tests, trial runs).

## Setup: "set up my skills"

1. Check `git --version`, `python3 --version`, `jq --version`. If one is
   missing, report it and stop.
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
7. Run `state.py stamp --repo <repo>`.
8. Report `claude --version` and offer `claude update`.
9. List the links made and say: restart Claude Code to load the new skills.

## Update: "update my skills"

1. Run `git -C <repo> pull --rebase --autostash -q`.
2. Run `sync_skill.py --all`, then `git -C <repo> diff --stat -- skills`.
   Summarize what changed in each skill.
3. On yes:
   - commit `chore: sync vendored skills`
   - run `git -C <repo> push -q`

   On no, run `git -C <repo> checkout -- skills`.
4. Run `link_skills.py`, `gen_catalog.py`, then `state.py stamp --repo <repo>`.

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
