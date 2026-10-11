# remove: ui-ux-pro-max (design)

- **Date:** 2026-10-12
- **Source:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill at `.claude/skills/ui-ux-pro-max`
- **Reviewed at commit:** `67803eac81607188194aea9842a723b89326d90d`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 1 | Design work recurs, but frontend-design and hallmark cover the same tasks with far less text. |
| Overlap | 0 | Claims "new page", "landing page" and UI review, the same prompts as frontend-design and hallmark. |
| Quality | 1 | Maintained, MIT. Every command runs `${CLAUDE_PLUGIN_ROOT}/.claude/skills/ui-ux-pro-max/scripts/search.py`, which is unset outside its own plugin, so a standalone install can't run its scripts. |
| Cost | 0 | Description 495 characters, over the 400 limit; body 214 lines plus CSV data files. |
| Safety | 2 | Local Python scripts reading bundled CSVs; no network. |
| Trial | n/a | Not run: Overlap and Cost already fail. |
| **Total** | 4/10 | |

## Verdict

remove, because it was dropped from core on 2026-10-12 and its scripts don't run outside its own plugin; frontend-design and hallmark cover the same prompts.
