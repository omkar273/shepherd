# reject: stop-slop (writing)

- **Date:** 2026-10-12
- **Source:** https://github.com/hardikpandya/stop-slop at `.` (repo root)
- **Reviewed at commit:** `8da1f030185bdfe8471220585162991eaeb970e9`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 1 | The owner asked for alternatives to humanizer; no task of its own. |
| Overlap | 1 | Same job as `humanizer`, which is already in the writing pack. |
| Quality | 2 | MIT, 2.6 KB `SKILL.md` and three short reference files, clear rules. Last changelog entry 2026-01-13. |
| Cost | 2 | Description 118 characters; references load on demand. |
| Safety | 2 | Read every file: markdown only, no scripts, hooks, or network calls, nothing aimed at the agent. |
| Trial | 0 | Scored 6, the same as the model alone. |
| **Total** | 8/12 | |

## Trial

- **Task:** rewrite a 193-word AI-sounding Ledgerly product-page draft with 8 facts, three fresh agents (no skill, `humanizer`, `stop-slop`).
- **Criteria, written before the run:** facts kept (0-2), tells removed (0-2), length within ±30% (135-251 words) (0 or 2), reads naturally (0-2); pass = +2 over both baseline and humanizer with facts at 2.
- **Without the skill:** 6/8. All 8 facts; no tells left; 108 words, below the limit.
- **With humanizer:** 5/8. All 8 facts; kept one "X, but also Y" contrast; 120 words, below the limit.
- **With stop-slop:** 6/8. All 8 facts; no tells left; 101 words, below the limit.

## Verdict

reject, because on the trial it did no better than the model alone, and it cut the text below the length limit like the others.
