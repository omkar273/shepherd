# reject: chart-visualization (data)

- **Date:** 2026-10-12
- **Source:** https://github.com/bytedance/deer-flow at `skills/public/chart-visualization`
- **Reviewed at commit:** `3f7a076972a927b4256df3e3c18b829186dd1355`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 1 | Charts come up in data work. |
| Overlap | 1 | The model already writes chart code directly. |
| Quality | 1 | Written for the deer-flow runtime (`/mnt/...` paths). |
| Cost | 2 | Short description. |
| Safety | 0 | `scripts/generate.js` line 37 posts the chart data to `https://antv-studio.alipay.com/api/gpt-vis`, a third-party service. |
| Trial | n/a | Not run: Safety fails. |
| **Total** | 5/10 | |

## Verdict

reject, because it sends the user's data to a third-party rendering API.
