# add: humanizer (writing)

- **Date:** 2026-10-12
- **Source:** https://github.com/blader/humanizer at `.` (repo root)
- **Reviewed at commit:** `225a6f39ac85f76ee48dbad772ea4abe4ed6c9d8`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 2 | The owner asked for it to be added. The user drafts posts and copy; rewriting AI-sounding text comes up. |
| Overlap | 2 | Trigger probe: it wins its own rewrite prompts and takes nothing else. |
| Quality | 2 | Maintained, MIT, versioned, with a package validator and CI. |
| Cost | 2 | Description 341 characters. |
| Safety | 2 | `SKILL.md` writes only to a file the user names and treats the text it edits as data. The repo root also brings inert extras: plugin manifests, `.github/`, `scripts/validate-package.py` (stdlib, no network). |
| Trial | 0 | Scored below the baseline. |
| **Total** | 10/12 | |

## Trial

- **Task:** rewrite an AI-sounding 85-word product paragraph about Ledgerly, keeping all 5 listed facts.
- **Criteria, written before the run:** facts kept (all 5, none invented), AI tells removed, length within ±30%, reads naturally; pass = +2 over baseline with facts at 2.
- **Without the skill:** 8/8. Every fact kept; one mild triad left; 18% shorter.
- **With the skill:** 7/8. Every fact kept; the same triad left; 33% shorter, outside the length limit.

## Verdict

add, at the owner's request below the bar: Trial is 0 (the model alone matched it on facts and cut less), but nothing else installed covers rewriting AI-sounding prose. Re-trial on two or three longer drafts with a length limit written in; remove it if it still doesn't beat the model alone.
