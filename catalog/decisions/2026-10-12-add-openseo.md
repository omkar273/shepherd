# add: openseo (seo)

- **Date:** 2026-10-12
- **Source:** https://github.com/every-app/open-seo at `plugins/openseo/skills/*` (12 skills: seo-project-setup, seo-coach, seo-audit, seo-report, keyword-research, keyword-clustering, competitor-analysis, competitive-landscape, link-prospecting, local-seo, ai-visibility-audit, ai-prompt-research)
- **Reviewed at commit:** `89e5a00717cdf049b7c2b4e29646edb3a7d4995b`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 2 | The owner asked for OpenSEO and for SEO and AEO coverage of their sites and products. |
| Overlap | 2 | No SEO skill is installed. No trigger probe run. The set routes among itself: `seo-coach` points to the workflow skills and every workflow delivers through `seo-report`. |
| Quality | 2 | MIT, maintained (pushed 2026-10-08), one `SKILL.md` per skill with explicit inputs, tool lists and anti-fabrication rules. |
| Cost | 1 | 11 of 12 descriptions are 70 to 342 characters. `ai-visibility-audit` is 417, over the 400 bar; it stays in because the set routes to it for AEO. Bodies load only on use. |
| Safety | 1 | Every file read. Prompt-only: no scripts, hooks or fetches. All data comes from OpenSEO's MCP server, which the user connects separately (hosted, or self-hosted with a DataForSEO key). Research tools spend usage credits; the skills check a 30-day research log first and ask before spending extra. They write to the user's OpenSEO project context (`update_project_context`) and `seo-report` links to openseo.so docs. |
| Trial | 0 | Not run. The skills need a live OpenSEO connection and credits. |
| **Total** | 8/12 | |

## Verdict

add, by the owner's decision below the bar (Cost 1, Safety 1, no trial). Re-trial `seo-audit` against a no-skill run on one real site once OpenSEO is connected; remove the set if it shows no gain.
