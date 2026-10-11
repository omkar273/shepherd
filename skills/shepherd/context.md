# Context hygiene

Every model gets worse as its context grows, not only slower. Keep context
small on purpose: what never lands in context costs nothing later.

## One task per session

- A new, unrelated task gets a fresh session. Before switching, write a
  handoff for the user to paste: goal, decisions, files changed, the commands
  that prove it works, and the next step.
- After two failed corrections on the same problem, stop. Write the handoff
  with what you learned and suggest a fresh session.
- When the user is about to step away from a large session, suggest a handoff:
  resuming a big session later re-sends all of it.

