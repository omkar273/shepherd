# add: scroll-craft (design)

- **Date:** 2026-10-12
- **Source:** https://github.com/nateherkai/scroll-craft at `plugins/nateherk-design/skills/scroll-craft`
- **Reviewed at commit:** `75d81f74e83692add18cd7a8a8e078b8a887a579`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 2 | The owner asked for it. |
| Overlap | 1 | It shares the landing-page cue with `frontend-design`; it is the narrower skill (scroll-driven, layered heroes, scrollytelling). No trigger probe run. |
| Quality | 2 | MIT, a clear `SKILL.md` with references read on demand, a changelog. |
| Cost | 0 | Description is about 850 characters, over the 400 bar; the body and references load only on use. |
| Safety | 1 | Ships node scripts (`kie.mjs`, `shoot.mjs`, `serve.mjs`, `doctor.mjs`) that were read: the only network calls go to `api.kie.ai` and `kieai.redpandaai.co` with the user's `KIE_AI_API_KEY` (read from env or a project `.env`) and spend credits; `shoot.mjs` and `doctor.mjs` launch Chrome and ffmpeg locally; `serve.mjs --lan` exposes a local server. Building from the user's own assets needs none of it. |
| Trial | 0 | Not run, by the owner's decision. |
| **Total** | 6/12 | |

## Verdict

add, by the owner's decision below the bar (Safety 1, Cost 0, no trial). Re-trial against `frontend-design` on a scroll-driven landing page and tighten the description; remove it if it shows no gain.
