# add: hyperframes (video)

- **Date:** 2026-10-12
- **Source:** https://github.com/heygen-com/hyperframes at `skills/hyperframes`
- **Reviewed at commit:** `2905162d925fc87fb8242e24ed0bbf025d307ea1`
- **License:** Apache-2.0

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 2 | The owner asked for a video editing and content creation section. |
| Overlap | 2 | Trigger probe, one fresh agent over 7 prompts: it takes "launch video from my site URL", "captions on an existing mp4" and "PR to changelog video"; it leaves a Next.js scroll reveal, a `.pptx` deck, a React CSS hover animation and a pagination bug to `shepherd` or `pptx`. |
| Quality | 2 | Maintained (pushed 2026-10-12), Apache-2.0, a clear 154-line `SKILL.md` and 16 reference files read on demand. HeyGen's own repo. |
| Cost | 1 | Description is 792 characters, over the 400 limit. The body and references load only on use. |
| Safety | 1 | The folder has no hooks and its only script that spawns a process, `plugin-cli.mjs`, is the plugin-install launcher. It tells the agent to run `npx hyperframes usage --json` at the start of every creation, `npx hyperframes skills update <workflow>` to fetch the workflow and core skills, and `npx hyperframes@latest upgrade --project .` to change a project's pinned CLI version, without asking in autonomous mode. Reviewed: `SKILL.md`, `skill-lifecycle.md`, `plugin-installation.md`, every non-test script; the other 22 files were only grepped for URLs, credentials, and exec patterns (no hits). |
| Trial | 0 | Not run. |
| **Total** | 8/12 | |

## Trial

- **Task:** not run.
- **Criteria, written before the run:** n/a.
- **Without the skill:** n/a.
- **With the skill:** n/a.

## Verdict

add, at the owner's request below the bar: Total is 8 and no trial was run, but no other skill covers rendering video from HTML. Only the router is vendored; the 20 workflow and domain skills it installs from upstream at run time (about 18 MB, with scripts) are not reviewed here. Re-trial with `npx hyperframes` available on "add captions to a 20-second talking-head clip" and "turn this PR into a changelog video"; remove it if it doesn't beat the model alone, or if the router keeps installing and upgrading without asking.
