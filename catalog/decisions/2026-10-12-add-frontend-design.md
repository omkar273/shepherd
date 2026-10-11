# add: frontend-design (design)

- **Date:** 2026-10-12
- **Source:** https://github.com/anthropics/skills at `skills/frontend-design`
- **Reviewed at commit:** `dbd4588f9e1033efb41dad4bef2f7947c8993d44`
- **License:** Apache-2.0

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 2 | The user builds landing pages and UI. |
| Overlap | 2 | Trigger probe: it wins new-page prompts; its only rival, hallmark, is rejected. |
| Quality | 2 | Maintained, Apache-2.0, a clear 71-line `SKILL.md`. |
| Cost | 2 | Description 204 characters; two files. |
| Safety | 2 | No scripts, hooks, network calls, or writes. |
| Trial | 1 | A tie with the baseline (9 vs 9), and one criterion below it. |
| **Total** | 11/12 | |

## Trial

- **Task:** a single-file landing page for Ledgerly, a privacy-first expense tracker for freelancers.
- **Criteria, written before the run:** visual direction, responsive at 375px, accessibility, honest content, self-contained; each 0-2; pass = +2 over baseline and no criterion below it. Judged blind (pages labelled A/B/C, self-identifying comments removed).
- **Without the skill:** 9/10. A ledger-paper page with no external requests; three small labels just under AA contrast.
- **With the skill:** 9/10. A "security envelope" page with the cleanest accessibility and a working demo, but the motif fades after the hero and it loads Archivo from an unpinned Google Fonts stylesheet (self-contained 1 vs 2).

## Verdict

add, by the owner's decision against the trial bar: it tied the model alone (9 vs 9) rather than beating it, but scored 11/12 with the best accessibility and a clean safety review. Re-trial on a harder design task; remove it if it still shows no gain.
