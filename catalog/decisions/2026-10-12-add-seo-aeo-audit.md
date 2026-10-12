# add: seo-aeo-audit (seo)

- **Date:** 2026-10-12
- **Source:** https://github.com/warpdotdev/oz-skills at `.agents/skills/seo-aeo-audit`
- **Reviewed at commit:** `6c08c49fc6c51b8f768bf8c53c041bc06a160765`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 2 | The owner asked for tools, not only guidance, for improving SEO and AEO. |
| Overlap | 1 | Overlaps `seo-aeo-best-practices` on guidance; adds audit scripts. No trigger probe run. |
| Quality | 2 | MIT, versioned, a long `SKILL.md` (752 lines) with JSON-LD templates. |
| Cost | 1 | Description is 187 characters, but the body is 752 lines when loaded. |
| Safety | 2 | Every file read. Three scripts: `lighthouse.sh` runs the local Lighthouse CLI; `pagespeed.sh` calls Google's PageSpeed API with the user's `PAGESPEED_API_KEY`; `search-console-export.mjs` calls the Search Console API with the user's `GSC_ACCESS_TOKEN`. Each exits if its key is missing; nothing else is fetched or executed. |
| Trial | 0 | Not run. |
| **Total** | 8/12 | |

## Verdict

add, by the owner's decision below the bar (Trial 0, Overlap 1, Cost 1). Re-trial against `seo-aeo-best-practices` on one page; remove the loser.
