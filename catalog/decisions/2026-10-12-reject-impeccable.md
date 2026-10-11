# reject: impeccable (design)

- **Date:** 2026-10-12
- **Source:** https://github.com/pbakaus/impeccable at `.claude/skills/impeccable`
- **Reviewed at commit:** `c63b8dd7dd5a5f3c32eaabe1af76d0694f863ed2`
- **License:** Apache-2.0

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 1 | Design work recurs. |
| Overlap | 0 | Claims the same new-page and redesign prompts as frontend-design and hallmark. |
| Quality | 2 | Maintained, detailed. |
| Cost | 0 | Description 895 characters, over twice the limit. |
| Safety | 0 | Step 1 runs a launcher that downloads a binary on first run (`SKILL.md` line 19); `/impeccable hooks` installs a detector hook that runs after UI edits (line 84). |
| Trial | n/a | Not run: Safety fails. |
| **Total** | 3/10 | |

## Verdict

reject, because it downloads and runs a binary and installs hooks, and its description alone is 895 characters.
