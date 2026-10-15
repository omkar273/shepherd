---
name: shepherd
description: Use when you write, change, or review code or docs in a repo, and your CLAUDE.md has no shepherd card. That includes a feature, a fix, a refactor, a review of a pull request, branch, or diff, and a plan for a multi-file change. Use it before you add a helper, wrapper, interface, layer, option, defensive check, or test that the task did not ask for. With the card, use it only for an audit, a multi-file plan, a correction from the user, SEO work, or a long session. Always use it to set up, update, add, prune, or check skills.
allowed-tools: Bash(python3 "${CLAUDE_SKILL_DIR}/hooks/capture.py" *)
hooks:
  UserPromptSubmit:
    - hooks:
        - type: command
          command: 'python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/shepherd}/hooks/capture.py" turn || true'
  Stop:
    - hooks:
        - type: command
          command: 'python3 "${CLAUDE_PLUGIN_ROOT:-$HOME/.claude/skills/shepherd}/hooks/capture.py" turn || true'
---

# Shepherd

Shepherd is one entry point. Route the task to the section or skill that owns
it, then follow that section or skill. Make the smallest change that does the
job, and wire it into the code that is already there. Cut before you add.

## Step 0, every time

```!
python3 "${CLAUDE_SKILL_DIR}/hooks/capture.py" step0 || true
```

1. The block above is the repo card and the lessons. If it shows no repo card,
   run `python3 <shepherd>/hooks/capture.py step0` from the repo
   (`<shepherd>` is the folder of this skill). Claude Code loads the root
   `CLAUDE.md` or `AGENTS.md`. Do not read it again. Before the first edit,
   read each nested `AGENTS.md` or `CLAUDE.md` from the card that is on the
   path to the change and not in context. Use the checks from the card. Repo
   rules win over this skill.
2. Do what the lessons say. The order of priority is: repo docs, then the
   never-cut list in `code/defensive.md`, then lessons, then this skill.
3. Docs go out of date. Before you use a file, helper, or mechanism that a doc
   names, make sure that it is in the code.
4. Recorded decisions (ADRs, architecture notes) win over the cut list. Do not
   flag what a recorded decision justifies. A new package or module boundary
   is a decision too. Add one in a feature change only when the user or a
   recorded decision asks for it.
5. If the repo has its own build or review skill or workflow (for example
   `.agents/skills/review`), follow its process and report format. Run
   shepherd's checks inside it.
6. Route:

| Situation | Read or use |
|---|---|
| Writing or changing code | `code/write.md`, `code/defensive.md` |
| Reviewing a PR or branch | `code/review.md`, `code/defensive.md` |
| Auditing a repo or a change (bugs, risk, scale, tests, bloat), or listing deferred shortcuts | `code/audit.md` |
| `.go` files or `go.mod` | + `lang/go.md` |
| `.ts` files | + `lang/typescript.md` |
| `.svelte`, `.svelte.ts` | + `lang/typescript.md`, `lang/svelte.md` |
| `.tsx`, `.jsx`, React imports | + `lang/typescript.md`, `lang/react.md` |
| Any other language | the code files only |
| Planning a multi-file or unclear change | the superpowers `brainstorming` skill, then `writing-plans`. If the repo uses Matt's issue flow, suggest `/to-spec` to the user. Only the user can start it. |
| A bug or a failing test | the superpowers `systematic-debugging` skill |
| About to say a change is done | the superpowers `verification-before-completion` skill |
| No skill in the listing fits the task | the keywords of the name-only skills from the SessionStart hook. If one fits, call it by name. Read only that skill. |
| "Set up", "update", "add" or "status" for skills | `skills.md` |
| Installing or removing a pack, or a task that fits a pack: planning, productivity, design, reverse engineering, video, writing, SEO, simulation | `skills.md`, Packs |
| Adding or removing a catalog skill | `curate.md` |
| SEO or AEO work on a site or product | `seo.md` |
| A long, slow, or messy session | `context.md` |
| The user corrects your work | `learn.md`, Record a correction. Do this before you reply. |
| "Consolidate shepherd lessons", "revert shepherd <commit>" | `learn.md` |

If a superpowers skill above is not installed, do its step yourself:

- Before an edit to many files, decide the goal and write a short plan.
- Before a fix, find the root cause.
- Before you say done, run the checks and read their output.

Read the `lang/` file before you write the first line in that language. Read
only the `lang/` files that match the change. Setup installs the `lang/` files
as path rules, so Claude Code loads each one when you open a matching file. If
a `lang/` file is in context, do not read it again. If a language has no file,
use the code files and the repo's own docs. Do not make up rules for a
language.

## Always on

- Write all prose in ASD-STE100 Simplified Technical English (STE): docs,
  comments, commit messages, PR bodies, findings, and reports. Read `ste.md`
  before the first sentence.
- Read a web page as text first. Take a screenshot only for a visual check, at
  scale 0.5 or less.
- Convert a PDF to text with `pdftotext`.
- Use Read to view source and Grep to search it. Do not use `cat` or `sed`
  for this.
- Do not read a file again just after you edit it.

## The ladder

Use the first rung that holds. Name that rung in one line:

1. Not needed: say so and stop.
2. Already in the repo: reuse it in the same way as the code around it.
   Extend the service or module that is there. Do not add a parallel one.
3. The standard library or platform.
4. A dependency that the repo already has.
5. Minimal new code.

## Shared cut list

This code does not earn its place. Look for it when you write and when you
review:

- An interface or abstract type with one implementation. Exception: the
  repo's convention requires it (a `createX` factory that returns interface
  `X`, service interfaces on the producer side). Exception: a test fake or
  stub implements it. Grep for implementations before you flag it.
- A factory with one product. A unit-of-work, manager, registry, or options
  layer with one consumer.
- A function that only forwards its arguments to one call.
- A one-expression helper with one or two callers that names no domain concept.
- Error factories, and helpers that only throw or only catch.
- A parameter, option, or flag that every caller leaves at its default.
- A generic type parameter that only one type fills.
- A new file or layer when a current file or layer already owns the job.
- Near-duplicates merged behind boolean flags. Keep the copies. A function
  split only to make it shorter.
- An alias that only renames: a re-export under a new name, a type alias or
  token that maps one name to another.
- A stub or placeholder: an option or branch that only logs "would do X", a
  hardcoded fake value. Leave it out until X exists.
- A comment that the code can carry instead, with a better name, a named
  constant, or a type. A comment earns its place only for a non-obvious why,
  an outside constraint, or a deliberate deviation. An outside constraint is a
  library bug, a spec, or an audit item. A TODO with an owner and a known
  shortcut also earn a place. Write a shortcut as
  `shortcut: <the limit>, <when to upgrade>`. Keep a comment to 2 lines or
  fewer. Delete commented-out code. Git keeps it.
- Logging on the happy path.
- Edits to code that the task did not ask about: refactors, renames, new
  formatting, and behavior changes to current paths. Also bulk removal of old
  comments or lint backlog in files that the change only touches.

## Proving code is unused

Grep does not find every reference. Before you call code unused, also check:

- side-effect imports (`import "./x"`)
- string-keyed registration (routes, DI names, event names)
- config globs and paths (Tailwind `@source`, build includes)
- reflection
- tests

If a removal can break something with no error, keep the code.

## Lint first

Run the repo's linter. Do not restate the rules that it enforces. Use judgment
for what lint cannot see: callers, invariants, reachability, scope, and
documented conventions that no linter enforces. In a review, a broken
documented convention is a finding. Quote the doc.
