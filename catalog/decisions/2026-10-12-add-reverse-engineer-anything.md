# add: reverse-engineer-anything (reverse-engineering)

- **Date:** 2026-10-12
- **Source:** https://github.com/morluto/rea at `.agents/skills/reverse-engineer-anything`
- **Reviewed at commit:** `b777e5d4d8a7b60edad7d5c0eaa56408a4b3f610`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 2 | The owner asked for it. |
| Overlap | 2 | Trigger probe: it wins "how does Obsidian.app's main process talk to the renderer"; it leaves a source-repo auth walkthrough alone, and a Go core dump goes to debugging first. |
| Quality | 2 | Maintained (pushed 2026-10-11), MIT. A clear 225-line `SKILL.md` and six reference files read on demand. The npm package `rea-agents` it names is published by `morluto` and links to this repo. |
| Cost | 2 | Description 300 characters; references load only for the matching target type. |
| Safety | 1 | No scripts or hooks in the skill folder. It drives the separate REA MCP server and CLI: with no `rea` installed it runs `npx -y rea-agents@latest` (unpinned, over the network); `rea setup --yes` writes client MCP config after a dry-run and approval; `observe_native_calls` and process capture run the target. Each is gated on the user's authorization. |
| Trial | 0 | Not run, by the owner's decision. |
| **Total** | 9/12 | |

## Trial

- **Task:** not run.
- **Criteria, written before the run:** n/a.
- **Without the skill:** n/a.
- **With the skill:** n/a.

## Verdict

add, by the owner's decision below the bar: Safety is 1 and no trial was run, but no other skill covers reverse engineering shipped apps and binaries, and every network, write, and execution step it takes waits for the user. Re-trial with `rea-agents` installed on a static question about a shipped Electron ASAR (Obsidian's `obsidian.asar`); remove it if it doesn't beat the model alone.
