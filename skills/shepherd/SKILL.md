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
| Planning a multi-file or unclear change | the superpowers `brainstorming` skill, then `writing-plans`; when the repo uses Matt's issue flow, suggest the user run `/to-spec` (user-invoked only) |
| A bug or a failing test | the superpowers `systematic-debugging` skill |
| About to say a change is done | the superpowers `verification-before-completion` skill |
| "Set up", "update", "add" or "status" for skills | `skills.md` |
| A long, slow, or messy session | `context.md` |

Read a `lang/` file before writing the first line in that language. Never read
a `lang/` file that doesn't match the change. For a language with no file, use
the code files and the repo's own docs; don't invent language rules.

## Always on

- Read a web page as text first; screenshot only for a visual check, at scale
  0.5 or less. Turn PDFs into text with `pdftotext`.
- View source with Read and search with Grep, not `cat` or `sed`. Don't
  re-read a file you just edited.

## The ladder

Take the first rung that holds, and name it in one line:

1. Not needed: say so and stop.
2. Already in the repo: reuse it the way neighbouring code does. Extend the
   existing service or module rather than adding a parallel one.
3. The standard library or platform.
4. A dependency the repo already has.
5. Minimal new code.

## Shared cut list

Code that has not earned its place, when writing and when reviewing:

- An interface or abstract type with one implementation. Exception: the repo's
  convention requires it (a `createX` factory returning interface `X`,
  producer-side service interfaces) or a test fake or stub implements it. Grep
  for implementations before flagging.
- A factory with one product; a unit-of-work, manager, registry, or options
  layer with one consumer.
- A function that only forwards its arguments to one call.
- A one-expression helper with one or two callers that names no domain concept.
- Error factories, throw-only and catch-only helpers.
- A parameter, option, or flag that every caller leaves at its default.
- A generic type parameter used with one type.
- A new file or layer when an existing one already owns the job.
- Near-duplicates merged behind boolean flags (keep the copies); a function
  split only to make it shorter.
- An alias that only renames: a re-export under a new name, a type alias or
  token that maps one name to another.
- A stub or placeholder: an option or branch that only logs "would do X", a
  hardcoded fake value. Leave it out until X exists.
- A comment the code could carry instead, through a better name, a named
  constant, or a type. A comment earns its place only for a non-obvious why,
  an outside constraint (a library bug, a spec, an audit item), a deliberate
  deviation, or a TODO with an owner, in at most 2 lines. Commented-out code
  is deleted; git remembers it.
- Logging on the happy path.
- Edits to code the task didn't ask about: refactors, renames, reformatting,
  behavior changes to existing paths, and bulk-stripping old comments or lint
  backlog in files you only touch.

## Proving code is unused

Grep misses some references. Before calling code unused, also check
side-effect imports (`import "./x"`), string-keyed registration (routes, DI
names, event names), config globs and paths (Tailwind `@source`, build
includes), reflection, and tests. If removing it would break something
silently, it stays.

## Lint first

Whatever the repo's linter enforces, run the linter instead of restating its
rules. Judgment covers what lint can't see: callers, invariants, reachability,
scope, and documented conventions that no linter enforces. In review, a broken
documented convention is a finding; quote the doc.
