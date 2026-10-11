# reject: docx, xlsx, pptx, pdf (docs and office)

- **Date:** 2026-10-12
- **Source:** https://github.com/anthropics/skills at `skills/{docx,xlsx,pptx,pdf}`
- **Reviewed at commit:** `dbd4588f9e1033efb41dad4bef2f7947c8993d44`
- **License:** proprietary (each `LICENSE.txt`: use governed by the user's agreement with Anthropic)

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 1 | Office files come up occasionally. |
| Overlap | 0 | The same skills already ship with the user's claude.ai account plugins, so a pack copy would duplicate them. |
| Quality | 1 | High quality, but the license doesn't allow redistribution through a third-party catalog. |
| Cost | 2 | Descriptions under 400 characters. |
| Safety | 2 | Local scripts only. |
| Trial | n/a | Not run: Overlap fails. |
| **Total** | 6/10 | |

## Verdict

reject, because the account plugins already provide these skills and their license is proprietary.
