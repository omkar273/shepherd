# reject: hallmark (design)

- **Date:** 2026-10-12
- **Source:** https://github.com/Nutlope/hallmark at `skills/hallmark`
- **Reviewed at commit:** `13ac0ec7e148655948100b6396439e481361d690`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 2 | The user builds landing pages and UI. |
| Overlap | 1 | Trigger probe: it and frontend-design both claim "new page"; at most one can join. |
| Quality | 1 | Maintained, MIT. Points to files it doesn't ship (`../../site/css/tokens.css`, `../../docs/`), and its theme-rotation rule depends on the missing `tokens.css`. |
| Cost | 1 | Description 258 characters, but 107 files (106 reference markdown files). |
| Safety | 1 | Generated pages hotlink third-party hosts, including the vendor's `usehallmark.com` and an unpinned `@tabler/icons@latest`; a footer template carries "Powered by Together AI"; some rules override user requests silently ("NOT bypassable"). |
| Trial | 0 | Scored below the baseline (8 vs 9). |
| **Total** | 6/12 | |

## Trial

- **Task:** a single-file landing page for Ledgerly, a privacy-first expense tracker for freelancers.
- **Criteria, written before the run:** visual direction, responsive at 375px, accessibility, honest content, self-contained; each 0-2; pass = +2 over baseline and no criterion below it. Judged blind (pages labelled A/B/C, self-identifying comments removed).
- **Without the skill:** 9/10. A ledger-paper page with no external requests; three small labels just under AA contrast.
- **With the skill:** 8/10. Bold Swiss-grid type and honest, labelled samples; no `nav` landmark, grid lines crossing body text, an unpinned Google Fonts request, and links to paths that don't exist in a single file.

## Verdict

reject, because its Safety is 1: generated pages call third-party hosts and can carry a vendor attribution.
