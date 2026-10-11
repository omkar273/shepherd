# shepherd

**Cut the bloat. Keep the checks.**

`shepherd` is an [Agent Skill](https://docs.claude.com/en/docs/claude-code/skills)
that makes your coding agent write the smallest change that works, and stops it
from deleting the checks that matter. It's built for Claude Code, and the
`skills` CLI installs it for other coding agents too.

## Sound familiar?

Coding agents are capable and eager, and the eagerness costs you:

- Wrappers, one-implementation interfaces, and helpers with a single caller.
- Defensive checks that can never fire, and, worse, removal of checks that
  matter, such as tenant scoping, because "another layer already does it".
- Code reviews that ask for more code: a shared helper, a new layer, more
  tests.
- Wiring gaps: a route that is never registered, an error code with no status.
- Sessions that grow until the model gets worse at the task.

## The receipts

Same prompts, fresh agents, scored against an answer key the agents never see.
Rerun them yourself with [`evals/README.md`](evals/README.md).

| | Without shepherd | With shepherd |
|---|---|---|
| Same feature, lines added (Go / TypeScript)\* | 310 / 132 | 125 / 59 |
| PR review: planted problems caught | 25 of 27 | 27 of 27 |
| PR review: tenant-scoping check flagged for removal | yes | no |

Without the skill, the agent's review asked the author to delete a tenant check
because another layer already ran it. That is the mistake `shepherd` exists to
stop: it cuts code that has not earned its place, and never cuts auth, tenant
scoping, money invariants, or cleanup.

\* Measured on 2026-10-11 with the same rules under their earlier name, `lean`.

## What you see

There is no command to remember. Ask for a feature, a fix, or a review as
usual; `shepherd` loads itself, and every change ends with a short report. For
example:

```text
Rung: already in the repo - reused scopeToTenant from store/query.go
Changed: internal/invoice/service.go - Void, one method
Lean: -41 lines cut in self-check
Fixed alongside: none
Follow-ups: none
Not checked: worker retry path, no test covers it
```

Reviews come back as a draft you approve before anything is posted, sorted
into MUST, SHOULD and ASK. Every fix deletes, inlines, moves, or wires code;
ideas that would add code go under "Outside lean".

## Quick start

### Just shepherd

One skill: no other skills, no `CLAUDE.md` block, no superpowers. In Claude
Code:

```bash
claude plugin marketplace add omkar273/shepherd
claude plugin install shepherd@shepherd
```

For other agents, use the [`skills`](https://github.com/vercel-labs/skills)
CLI. It detects which of its supported agents you have installed, such as
Codex, Cursor, Gemini CLI, and OpenCode, and asks you to pick if it finds none:

```bash
npx skills add https://github.com/omkar273/shepherd --skill shepherd -g
```

Drop `-g` to install it for the current project only. Without the
[superpowers](https://github.com/obra/superpowers) plugin, `shepherd` does the
planning, debugging, and verification steps itself instead of handing them
off.

### The full setup

`shepherd`, Matt Pocock's engineering skills, superpowers, packs, and the
"update my skills" and "skills status" commands. If you installed the plugin
above, uninstall it first; the full setup includes `shepherd`.

```bash
git clone https://github.com/omkar273/shepherd ~/src-code/shepherd
```

You need Claude Code, git, Python 3, and jq; setup stops if one is missing.
Open Claude Code in that folder and say **"set up my skills"**. Setup:

- shows what it will link and back up, and continues on your yes
- links each skill into `~/.claude/skills` and `~/.agents/skills`
- moves anything it would replace to `~/.skills-backup/<date>/`, and never
  deletes your files
- writes one marked block into `~/.claude/CLAUDE.md`
- offers to install the [superpowers](https://github.com/obra/superpowers)
  plugin if it is missing
- offers the 7-day update reminder, showing the `~/.claude/settings.json`
  diff first

Running setup again is safe: it skips what's already in place.

## How it works

```mermaid
flowchart LR
  task[Your task] --> router{shepherd}
  router -->|write or change code| write[code/write.md]
  router -->|review a PR| review[code/review.md]
  write --> rules[code/defensive.md + lang/*]
  review --> rules
  router -->|plan, debug, verify| sp[superpowers skills]
  router -->|long or messy session| ctx[context.md]
  router -->|set up or update skills| mgmt[skills.md]
```

The router stays under 5,000 tokens, which is what Claude Code keeps after it
compacts a session. Everything else loads only when the task needs it, and a
Go change never loads the TypeScript rules.

The rules, briefly:

- **The ladder:** not needed, then already in the repo, then the standard
  library, then an existing dependency, then minimal new code.
- **The cut list:** one-implementation interfaces, pass-through functions,
  one-caller helpers, flags nobody sets, stubs, comments that restate code,
  edits nobody asked for.
- **The never-cut list:** authentication, tenant scoping, money invariants,
  state guards, rollback and cleanup, even when another layer also checks.
- **The diff contract:** the requested behavior, correct under failure; its
  wiring; tests the repo requires; adjacent bug fixes, each named. Nothing
  else.

## What setup also gives you

`shepherd` hands planning, debugging, and the final done-check to the
[superpowers](https://github.com/obra/superpowers) skills. Setup also links
Matt Pocock's engineering skills, such as `grilling`, `prototype`, `research`,
and `pr`. His slash-command skills, such as `/grill-me` and `/to-spec`, come
as [packs](#packs-experimental).

Skills marked `mine` are authored here. Vendored skills record their source in
`.origin.yaml` and are re-synced, never edited by hand.

<details>
<summary>Every skill in this repo</summary>

<!-- CATALOG:START -->

### Mine

| Skill | Description | Source |
| --- | --- | --- |
| `shepherd` | Use when writing, changing, or reviewing code in any repo - implementing a feature or fix, refactoring, reviewing a teammate's pull request, a branch, or a diff (before or alongside code-review), debugging, planning a multi-file change, or wrapping up a change before saying it is done - whenever about to add a helper, wrapper, interface, layer, option, defensive check, or test the task did not ask for, and when setting up, updating, adding, or checking skills. | local |

### Vendored

| Skill | Description | Source |
| --- | --- | --- |
| `codebase-design` | Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module's interface, find deepening opportunities, decide where a seam goes, make code more testable or AI-navigable, or when another skill needs the deep-module vocabulary. | https://github.com/mattpocock/skills |
| `domain-modeling` | Build and sharpen a project's domain model. Use when discussing codebase terminology, writing or editing a GLOSSARY.md, or recording or editing an ADR. | https://github.com/mattpocock/skills |
| `git-guardrails-claude-code` | Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute. Use when user wants to prevent destructive git operations, add git safety hooks, or block git push/reset in Claude Code. | https://github.com/mattpocock/skills |
| `grilling` | Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases. | https://github.com/mattpocock/skills |
| `pr` | Use when writing a PR body. | https://github.com/mattpocock/skills |
| `prototype` | Build a throwaway prototype to answer a design question. Use when the user wants to sanity-check whether a state model or logic feels right, or explore what a UI should look like. | https://github.com/mattpocock/skills |
| `research` | Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent. | https://github.com/mattpocock/skills |
| `setup-pre-commit` | Set up Husky pre-commit hooks with lint-staged (Prettier), type checking, and tests in the current repo. Use when user wants to add pre-commit hooks, set up Husky, configure lint-staged, or add commit-time formatting/typechecking/testing. | https://github.com/mattpocock/skills |
| `wizard` | Generate an interactive bash wizard that walks a human through steps only they can perform. Use when provisioning infrastructure, setting up credentials or CI secrets, walking an unfamiliar third-party dashboard, or running a one-off migration or cutover. Don't invoke this for steps the agent can perform itself. | https://github.com/mattpocock/skills |
| `writing-for-agents` | Writing documents for agents. Use when creating or editing skills, or modifying AGENTS.md or CLAUDE.md. | https://github.com/mattpocock/skills |

<!-- CATALOG:END -->

</details>

## Keeping it current

- **"update my skills"** pulls this repo, re-syncs vendored skills from their
  sources, shows you the diff, and commits and pushes on your yes.
- **"skills status"** reports missing, broken, or shadowed links, vendored
  skills behind their source, installed and available packs, and days since
  the last update.
- Optionally, a session-start nudge reminds you after 7 days.
- **Just shepherd:** `claude plugin update shepherd@shepherd`, or
  `npx skills update shepherd`.

## Packs (experimental)

Packs are skills that install only when you need them. The catalog has two:

- **planning:** Matt Pocock's issue flow: `/to-spec`, `/to-tickets`,
  `/implement`, `/wayfinder`, `/triage`, and 5 more.
- **productivity:** `/grill-me`, `/handoff`, `/teach`, `/to-questionnaire`,
  `/wait-what`, and `/retro`.

When a task fits a pack you don't have, `shepherd` offers it once per session
and never installs without your yes. You can also say **"what packs are
there"**, **"install the planning pack"**, or **"remove a pack"**. Packs come
with the full setup; a shepherd-only install doesn't offer them.

Packs track each skill's upstream. Every skill in a pack has a decision record
in [`catalog/decisions/`](catalog/decisions/) that scores it against a rubric
and names the commit reviewed. The procedure is in
[`curate.md`](skills/shepherd/curate.md).

## Add value

The contributions that help most:

1. **A check `shepherd` cut that mattered**, or one it should have cut: open
   a bug report with the code shape.
2. **A language file:** `skills/shepherd/lang/<language>.md` with the same four
   headings (keep, cut, boundaries, wiring).
3. **An eval fixture** for a stack the evals don't cover yet; see
   [Adding a case](evals/README.md#adding-a-case).
4. **A skill proposal:** use the skill request form.

Read [CONTRIBUTING.md](CONTRIBUTING.md) before you start. Everyone involved
follows the [code of conduct](CODE_OF_CONDUCT.md). Report vulnerabilities as
described in [SECURITY.md](SECURITY.md).

## Uninstall

Just shepherd: `claude plugin uninstall shepherd@shepherd`, or
`npx skills remove shepherd -g`.

The full setup: remove the links into this clone and into the pack cache, then
the session-start reminder, if you turned it on.

```bash
find ~/.claude/skills ~/.agents/skills -maxdepth 1 \( -lname "$HOME/src-code/shepherd/*" -o -lname "$HOME/.shepherd/catalog/*" \) -delete
python3 ~/src-code/shepherd/skills/shepherd/scripts/settings.py remove-hook --event SessionStart --command 'python3 "$HOME/.claude/skills/shepherd/scripts/nudge.py"' --write
```

Then delete the block between `<!-- skills:begin -->` and
`<!-- skills:end -->` in `~/.claude/CLAUDE.md`. The pack cache is in
`~/.shepherd/`, and anything setup replaced is in `~/.skills-backup/`.

## Credits and license

- Engineering and productivity skills by
  [Matt Pocock](https://github.com/mattpocock/skills), MIT.
- [superpowers](https://github.com/obra/superpowers) by Jesse Vincent,
  installed as a plugin rather than vendored.

Released under the [MIT License](LICENSE). Vendored skills keep their own
licenses. Not affiliated with `shepherd-agents/shepherd`.
