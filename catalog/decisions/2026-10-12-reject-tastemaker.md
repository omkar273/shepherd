# reject: tastemaker (design)

- **Date:** 2026-10-12
- **Source:** https://github.com/codeswithroh/tastemaker at `skills/tastemaker`
- **Reviewed at commit:** `792a28a820ec4e9159ef8621c21a6c88528bbf2e`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 1 | Same landing-page and UI cue as the rest of the pack. |
| Overlap | 0 | Its description triggers on "build the frontend", "make this look good", and "match this vibe": it would steal `frontend-design`'s prompts. |
| Quality | 2 | Maintained, MIT, structured references. |
| Cost | 0 | Description is over 900 characters; 76 files. |
| Safety | 1 | About 25 Python and JS helpers. `fetch_photos.py` calls Openverse and Pixabay (optional `PIXABAY_API_KEY`); it ships a `_netguard.py`. Not fully read. |
| Trial | n/a | Not run. |

## Verdict

reject, because its trigger is broader than `frontend-design`'s, its description is over twice the cost bar, and it ships unread network scripts.
