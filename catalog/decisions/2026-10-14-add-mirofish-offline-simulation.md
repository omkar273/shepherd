# add: mirofish-offline-simulation (simulation)

- **Date:** 2026-10-14
- **Source:** https://github.com/aradotso/trending-skills at `skills/mirofish-offline-simulation`
- **Reviewed at commit:** `c61b1a456af4015e9a367e0245292281bb3c87d9`
- **License:** none declared on the skill repo; the project it documents (`nikmcfly/MiroFish-Offline`) is AGPL-3.0

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 2 | The owner asked for it. |
| Overlap | 2 | No installed skill covers multi-agent opinion simulation. No trigger probe run; its triggers are all MiroFish-specific phrases. |
| Quality | 0 | Third-party write-up by ara.so of a fork, not by the MiroFish authors; the skill repo declares no license; documents a pre-1.0 project with no published accuracy figures. |
| Cost | 1 | Description is under 400 characters; the body is about 17 KB and loads only on use. |
| Safety | 2 | One `SKILL.md`, read in full. Only setup docs and API examples: `docker compose`, `docker run`, `ollama pull`, `pip install`, local `curl` to `localhost:5000`. No scripts, hooks, or instructions aimed at the agent. Caveat for the user: the manual `docker run` publishes Neo4j on all host interfaces with the password `mirofish`; bind it to `127.0.0.1` and change the password. |
| Trial | 0 | Not run: the recommended path needs Neo4j and Ollama with a 14B to 32B model (10 to 24 GB VRAM). A 7B or CPU run is possible but slow and lower quality, so it would not show the skill's intended output. |
| **Total** | 7/12 | |

## Verdict

add, by the owner's decision below the bar (Quality 0, Trial 0). The skill only documents a project the user must install and run themselves. Remove it if the skill repo stays unlicensed, the pinned project goes unmaintained, or a trial on a real document shows no gain over reading the project's README.
