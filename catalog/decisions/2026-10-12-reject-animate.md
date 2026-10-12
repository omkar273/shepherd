# reject: animate (design)

- **Date:** 2026-10-12
- **Source:** https://github.com/emilkowalski/skills at `skills/animate`
- **Reviewed at commit:** `2d228630ba1446365f614a108cb8252f1feda202`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 1 | Motion work recurs, but `emil-design-eng` already carries the same framework. |
| Overlap | 0 | Same easing, duration, and "should it animate" gate as `emil-design-eng`; would double-fire. |
| Quality | 1 | Hands off to `pick-ui-library`, `review-animations`, and `improve-animations`, none of which ship with it. |
| Cost | 1 | Description is about 430 characters. |
| Safety | 2 | Two markdown files, no scripts or network calls. |
| Trial | n/a | Not run. |

## Verdict

reject, because it repeats `emil-design-eng` and leans on three sibling skills that are not vendored.
