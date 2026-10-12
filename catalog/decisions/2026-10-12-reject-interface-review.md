# reject: interface-review (design)

- **Date:** 2026-10-12
- **Source:** https://github.com/jakubkrehel/skills at `skills/interface-review`
- **Reviewed at commit:** `c0588bb6d654eb725046f0bf9deec338c34891ab`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 1 | Diff-scoped UI review is useful, but the repo has code review skills. |
| Overlap | 1 | `disable-model-invocation: true`, so it never fires by itself. |
| Quality | 2 | Maintained, careful scope rules. |
| Cost | 2 | Description is 190 characters. |
| Safety | 2 | Markdown only. |
| Trial | n/a | Not run. |

## Verdict

reject, because it hands its findings to `better-interface` and the `better-*` suite, which are not vendored; it is a one-skill slice of a seven-skill system.
