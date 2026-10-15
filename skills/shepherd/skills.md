# Skills: setup, update, add, status

`<shepherd>` is the folder that contains this file: `skills/shepherd` in the
clone, or `~/.claude/skills/shepherd` after installation. `<repo>` is the root
of the clone. Run scripts with `python3 <shepherd>/scripts/<script>`. Every
script takes `--home <dir>`. Pass it only when an instruction tells you to
(tests, trial runs).

Every flow below needs the clone. First run
`test -f <shepherd>/../../setup/claude-md.md`. If it fails, the user installed
shepherd on its own (with `npx skills` or as a plugin). In that case:

1. Do not run a script from this folder.
2. Tell the user that these flows come with the full setup in the README.
3. For an update, give them the command for the tool that installed shepherd:
   `npx skills update shepherd` or `claude plugin update shepherd@shepherd`.
4. Stop.

## Setup: "set up my skills"

1. Check `git --version` and `python3 --version`. If one of them is not
   installed, report it and stop. If `jq --version` fails, say that the
   `git-guardrails-claude-code` hook needs it, and continue.
2. Run `link_skills.py --dry-run --retire`. Show the user what the script will
   link, back up (with the backup path), retire, and prune. If the user says
   yes, continue.
3. Run `link_skills.py --retire`.
4. CLAUDE.md:
   - If `~/.claude/CLAUDE.md` has an old `## Lean code` block outside the
     `<!-- skills:begin -->` markers, show it. If the user says yes, remove it.
   - Run `claude_md.py`.
5. Superpowers: if `superpowers:brainstorming` is not in your available
   skills and the user says yes, run
   `claude plugin marketplace add obra/superpowers-marketplace` and then
   `claude plugin install superpowers@superpowers-marketplace`.
6. Update nudge:
   - Run `settings.py add-hook --event SessionStart --command 'python3 "$HOME/.claude/skills/shepherd/scripts/nudge.py"'`.
     Show the diff that it prints.
   - If the user says yes, run it again with `--write`.
7. Context hooks (`context.md` says what each hook does). For each row, run
   `settings.py add-hook` with the arguments in the row, and show the diff. If
   the user says yes, run it again with `--write`:
   - `--event UserPromptSubmit --command 'python3 "$HOME/.claude/skills/shepherd/scripts/context_hooks.py" warn'`
   - `--event PostToolUse --matcher Bash --command 'python3 "$HOME/.claude/skills/shepherd/scripts/context_hooks.py" trim'`
   - `--event PreToolUse --matcher Bash --command 'python3 "$HOME/.claude/skills/shepherd/scripts/context_hooks.py" guard'`
8. Auto-compact: run `settings.py merge --json '{"env": {"CLAUDE_AUTOCOMPACT_PCT_OVERRIDE": "70"}}'`.
   Show the diff. If the user says yes, run it again with `--write`. If
   `~/.claude/settings.json` still has `autoCompactWindow: 300000` from an
   earlier setup, show it. If the user says yes, remove it.
9. Status line: ask the user whether they want context % in the status line.
   Say that the context warning learns the window size of the model from the
   status line. Without it, the warning assumes 200k. If the user says yes,
   run `settings.py merge --json '{"statusLine": {"type": "command", "command": "python3 \"$HOME/.claude/skills/shepherd/scripts/context_hooks.py\" statusline"}}'`.
   Show the diff. If the user says yes, run it again with `--write`.
10. Run `state.py stamp --repo <repo>`.
11. Report the version from `claude --version`, and offer `claude update`.
12. List the links that setup made, and say: restart Claude Code to load the
    new skills.
13. Ask the user which repos they work in most. Offer the Prune flow one time
    for each of these repos.

## Update: "update my skills"

1. Run `git -C <repo> pull --rebase --autostash -q`.
2. Run `GIT_TERMINAL_PROMPT=0 git -C <repo> push --dry-run -q`. If it fails,
   go to step 4, because the user cannot push from this clone. Their vendored
   updates come with the pull, and the clone stays a clean copy of upstream.
3. Sync vendored skills:
   - Run `sync_skill.py --all` and `gen_catalog.py`. Then run
     `git -C <repo> diff --stat -- skills README.md`. Summarize what changed
     in each skill.
   - If the user says yes, commit the synced skills and the catalog with the
     message `chore: sync vendored skills`. Then run `git -C <repo> push -q`.
   - If the user says no, run `git -C <repo> checkout -- skills`. Then run
     `gen_catalog.py`.
4. Run `link_skills.py`. Then run `state.py stamp --repo <repo>`.

## Add: "add skill X"

- For your own skill, run `new_skill.py <name> --origin mine`. Then write its
  `SKILL.md`.
- For a vendored skill, run
  `new_skill.py <name> --origin vendored --source-repo <url>
  --source-path <path> --source-ref <sha> --seed-from <local checkout of path>`.
- Then run `link_skills.py` and `gen_catalog.py`. Run the tests from
  `<repo>/AGENTS.md`. Then commit.

## Status: "skills status"

Run `status.py`. To compare vendored skills with their sources, add
`--remote`. Summarize:
- missing, broken, or shadowed links
- vendored skills that are behind their source
- uncommitted changes
- days since the last update

## Prune: "prune skills for this repo"

Each turn sends the name and the description of each skill. Prune keeps the
description only for the skills that the repo needs. The other skills show
only their names. An agent can still call such a skill by its name.

Do not set a skill to `"off"`. An agent selects a skill from its description.
Nothing can start a skill that is off.

1. Ask the user which other skills the repo needs now. For example, SEO work
   needs `seo-*` and `keyword-*`. Use these glob patterns as `<patterns>`. If
   the user names no skills, do not use `--keep`.
2. Run `status.py --catalog --repo <the repo> --keep <patterns>`. It reads the
   last 30 days of transcripts for that repo locally. It reports only names
   and counts. Never quote transcript text.
3. Show the user these keys of the report:
   - `keep`: the user, project, and builtin skills that keep their
     descriptions. These are shepherd, the skills that the routing table in
     `SKILL.md` names, the skills that the repo used, and the `--keep` matches.
   - `app_plugins`: each unused plugin that has no `key`, with its number of
     skills. These plugins came with the desktop app, and a settings file
     cannot turn them off. Tell the user to turn them off in the plugin
     settings of the Claude app. That change applies to all repos.
4. Run `settings.py merge --file <the repo>/.claude/settings.local.json --json "$(python3 <shepherd>/scripts/status.py --catalog --repo <the repo> --keep <patterns> --patch)"`.
   Show the diff. The patch makes these changes:
   - It sets `"name-only"` in `skillOverrides` for each other user, project,
     and builtin skill.
   - It removes the `"name-only"` override of each kept skill.
   - It sets `false` in `enabledPlugins` for each unused plugin that has a
     `key`. A plugin with a kept skill stays on.
   The patch does not change an `"off"` override. `skillOverrides` does not
   apply to plugin skills.
5. If the user says yes, run the command again with `--write`. Do not write
   anything without that yes. Tell the user that the change applies to new
   sessions.

## Unhide: "unhide X", "show the description of X"

1. Run `settings.py merge --file <the repo>/.claude/settings.local.json --json '{"skillOverrides": {"X": null}}'`.
   The `null` removes the override of X. Show the diff.
2. If the user says yes, run the command again with `--write`.
3. Tell the user: if the repo does not use X, the next prune sets X to
   `"name-only"` again. To prevent this, add X to `--keep` in that prune.

## Packs: "install the <pack> pack", "remove a pack", "what packs are there"

- **List:** `catalog.py list` shows each pack, its skills, and whether the
  pack is installed.
- **Install:** say which skills the pack adds. Wait for a yes. Then run
  `catalog.py install <pack>`, and report what it linked and backed up. If a
  new skill does not appear in the session, say: restart Claude Code to load
  it.
- **Remove:** `catalog.py uninstall <pack>` removes only the pack's links.
- **Clean the cache:** run `catalog.py prune` only when the user asks.
- **Add or remove a catalog skill:** follow `curate.md`.
