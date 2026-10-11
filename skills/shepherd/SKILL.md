---
name: shepherd
description: Use for any coding task in any repo - writing, changing, reviewing, planning, debugging, or finishing a change - for setting up, updating, adding, or checking skills, and when a session grows long or messy.
---

# Shepherd

One entry point. Route the task to the section or skill that owns it, then
follow that. The smallest change that does the job, wired into the code that
already exists. Subtract before you add.

## Step 0, every time

1. Read the repo's root `CLAUDE.md` / `AGENTS.md`, then every `AGENTS.md` on
   the path from the root down to each directory you touch. Read its lint
   config and its check scripts (Makefile, `package.json` scripts, CI
   workflow). Repo rules beat this skill.
2. Docs drift. Before relying on a file, helper, or mechanism a doc names,
   confirm it exists in the code.
3. Recorded decisions (ADRs, architecture notes) beat the cut list: don't flag
   what one justifies. A new package or module boundary is itself a decision;
   don't create one inside a feature change unless the user or a recorded
   decision asks for it.
4. If the repo ships its own build or review skill or workflow (for example
   `.agents/skills/review`), follow its process and report format; shepherd's
   checks run inside it.
5. Route:

| Situation | Read or use |
|---|---|
| Writing or changing code | `code/write.md`, `code/defensive.md` |
| Reviewing a PR or branch | `code/review.md`, `code/defensive.md` |
| `.go` files or `go.mod` | + `lang/go.md` |
| `.ts` files | + `lang/typescript.md` |
| `.svelte`, `.svelte.ts` | + `lang/typescript.md`, `lang/svelte.md` |
| `.tsx`, `.jsx`, React imports | + `lang/typescript.md`, `lang/react.md` |
| Any other language | the code files only |
| Planning a multi-file or unclear change | the superpowers `brainstorming` skill, then `writing-plans`; Matt's `to-spec` when the repo uses his issue flow |
| A bug or a failing test | the superpowers `systematic-debugging` skill |
| About to say a change is done | the superpowers `verification-before-completion` skill |
| "Set up", "update", "add" or "status" for skills | `skills.md` |
| A long, slow, or messy session | `context.md` |

Read a `lang/` file before writing the first line in that language. Never read
a `lang/` file that doesn't match the change. For a language with no file, use
the code files and the repo's own docs; don't invent language rules.

