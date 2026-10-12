# add: better-layout (design)

- **Date:** 2026-10-12
- **Source:** https://github.com/jakubkrehel/skills at `skills/better-layout`
- **Reviewed at commit:** `c0588bb6d654eb725046f0bf9deec338c34891ab`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 1 | Layout correctness (clipping, RTL, safe areas, breakpoints) is where generated UI usually fails; no specific session asked for it. |
| Overlap | 1 | No installed skill covers layout rules; `frontend-design` is aesthetic. It names sibling `better-*` skills only as scope boundaries and works without them. No trigger probe run. |
| Quality | 2 | MIT, maintained, short `SKILL.md` plus two reference files loaded on demand, with a severity and report format. |
| Cost | 2 | Description is 170 characters; four files. |
| Safety | 2 | Markdown only, no scripts, hooks, network calls, or installs. `SKILL.md` and `spacing-and-adaptivity.md` read; `grouping-and-alignment.md` pattern-scanned. |
| Trial | 0 | Not run, by the owner's decision. |
| **Total** | 8/12 |  |

## Verdict

add, by the owner's decision below the bar (no trial). Re-trial on a responsive page at 320px and RTL; remove it if it finds nothing a plain review misses.
