# skills repo

- Setup, update, add and status go through `skills/shepherd/skills.md`.
- Every skill is one folder under `skills/`. Vendored skills carry an
  `.origin.yaml`; never edit them by hand, re-sync them with
  `skills/shepherd/scripts/sync_skill.py`.
- `skills/shepherd` is authored here (`origin: mine`).
- After adding or removing a skill, regenerate the README catalog with
  `skills/shepherd/scripts/gen_catalog.py`.
- Tests:
  `python3 -m unittest discover -s skills/shepherd/scripts/tests`
- Commits and PR bodies never name a model and never carry a
  `Co-Authored-By:` or "Generated with" trailer.
