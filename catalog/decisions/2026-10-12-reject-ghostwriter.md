# reject: ghostwriter (content)

- **Date:** 2026-10-12
- **Source:** https://github.com/mblode/agent-skills at `skills/ghostwriter`
- **Reviewed at commit:** `872bc83bdb6dd54a9ff456fbf1181beea6db7875`
- **License:** MIT

## Scores

| Criterion | Score | Evidence |
|---|---|---|
| Need | 2 | The user writes LinkedIn posts and updates in their own voice. |
| Overlap | 0 | Trigger probe: its description claims READMEs, docs, tickets and review comments, so it pulls tasks from `pr`, the documentation plugin and the LinkedIn writer, and competes with humanizer on rewrites. |
| Quality | 2 | Maintained, MIT, clear structure. |
| Cost | 2 | Description 388 characters. |
| Safety | 1 | Writes voice profiles to `~/.config/ghostwriter` (confirmed once, with a backup); names skills that won't be installed (`product-design`, `pr-creator`, `presentation-creator`). |
| Trial | 1 | A tie with the baseline. |
| **Total** | 8/12 | |

## Trial

- **Task:** a LinkedIn post announcing Ledgerly 2.0 in the user's voice, from three sample posts and a fact brief.
- **Criteria, written before the run:** voice match (short sentences, no emojis or hashtags, plain first-person claims), facts only from the brief, no AI tells, under 120 words; pass = +2 over baseline.
- **Without the skill:** 8/8. Short, plain, every fact from the brief, no tells.
- **With the skill:** 8/8. Nearly the same post in fewer words.

## Verdict

reject, because it ties the baseline on the trial and its description pulls documentation and PR tasks away from the skills that own them.
