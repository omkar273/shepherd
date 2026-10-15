# skills repo

- Use `skills/shepherd/skills.md` for setup, update, add, and status.
- Each skill is one folder under `skills/`. A vendored skill has an
  `.origin.yaml`. Do not edit a vendored skill by hand. Sync it again with
  `skills/shepherd/scripts/sync_skill.py`.
- This repo is the source of `skills/shepherd` (`origin: mine`). When you ship
  a change to it, raise `version` in
  `skills/shepherd/.claude-plugin/plugin.json`. Plugin users get the change
  only after the version changes.
- Write the prose of an authored skill, this file, and `setup/claude-md.md` in
  ASD-STE100 Simplified Technical English. `skills/shepherd/ste.md` has the
  rules. `skills/shepherd/scripts/ste_lint.py` checks them, and the tests run
  it.
- After you add or remove a skill, or change a skill's description,
  regenerate the README catalog with `skills/shepherd/scripts/gen_catalog.py`.
- Run the checks with:
  `python3 -m unittest discover -s skills/shepherd/scripts/tests` and
  `ruff check .`. CI runs them on each pull request.
- Do not name a model in a commit or a PR body. Do not add a
  `Co-Authored-By:` or "Generated with" trailer.
