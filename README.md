# skills

One skill to rely on, `shepherd`, plus the skills it routes to. Clone this repo
on any machine and tell your agent "set up my skills".

`shepherd` is not affiliated with `shepherd-agents/shepherd`.

## Setup

```bash
git clone https://github.com/omkar273/skills ~/src-code/skills
```

Then, in Claude Code inside the clone: "set up my skills". Setup links every
skill into `~/.claude/skills` and `~/.agents/skills`, backs up anything it
replaces, and shows every settings change before writing it.

## Skills

<!-- CATALOG:START -->

### Mine

| Skill | Description | Source |
| --- | --- | --- |
| `shepherd` | Use when writing, changing, or reviewing code in any repo - implementing a feature or fix, refactoring, reviewing a pull request or branch, debugging, planning a multi-file change, or wrapping up a change before saying it is done - whenever about to add a helper, wrapper, interface, layer, option, defensive check, or test the task did not ask for, and when setting up, updating, adding, or checking skills. | local |

### Vendored

| Skill | Description | Source |
| --- | --- | --- |
| `ask-matt` | Ask which skill or flow fits your situation. A router over the skills in this repo. | https://github.com/mattpocock/skills |
| `codebase-design` | Shared vocabulary for designing deep modules. Use when the user wants to design or improve a module's interface, find deepening opportunities, decide where a seam goes, make code more testable or AI-navigable, or when another skill needs the deep-module vocabulary. | https://github.com/mattpocock/skills |
| `domain-modeling` | Build and sharpen a project's domain model. Use when discussing codebase terminology, writing or editing a GLOSSARY.md, or recording or editing an ADR. | https://github.com/mattpocock/skills |
| `frontend-design` | Guidance for distinctive, intentional visual design when building new UI or reshaping an existing one. Helps with aesthetic direction, typography, and making choices that don't read as templated defaults. | local |
| `git-guardrails-claude-code` | Set up Claude Code hooks to block dangerous git commands (push, reset --hard, clean, branch -D, etc.) before they execute. Use when user wants to prevent destructive git operations, add git safety hooks, or block git push/reset in Claude Code. | https://github.com/mattpocock/skills |
| `graphify` | any input (code, docs, papers, images, videos) to knowledge graph. Use when user asks any question about a codebase, documents, or project content - especially if graphify-out/ exists, treat the question as a /graphify query. | local |
| `grill-me` | A relentless interview to sharpen a plan or design. | https://github.com/mattpocock/skills |
| `grill-with-docs` | A relentless interview to sharpen a plan or design, which also creates docs (ADR's and glossary) as we go. | https://github.com/mattpocock/skills |
| `grilling` | Grill the user relentlessly about a plan, decision, or idea. Use when the user wants to stress-test their thinking, or uses any 'grill' trigger phrases. | https://github.com/mattpocock/skills |
| `handoff` | Compact the current conversation into a handoff document for another agent to pick up. | https://github.com/mattpocock/skills |
| `implement` | Implement a piece of work based on a spec or set of tickets. | https://github.com/mattpocock/skills |
| `implement-spec` | Implement the result of /to-spec and /to-tickets in code. | https://github.com/mattpocock/skills |
| `improve-codebase-architecture` | Scan a codebase for deepening opportunities, present them as a visual HTML report, then grill through whichever one you pick. | https://github.com/mattpocock/skills |
| `pr` | Use when writing a PR body. | https://github.com/mattpocock/skills |
| `prototype` | Build a throwaway prototype to answer a design question. Use when the user wants to sanity-check whether a state model or logic feels right, or explore what a UI should look like. | https://github.com/mattpocock/skills |
| `research` | Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or reading legwork delegated to a background agent. | https://github.com/mattpocock/skills |
| `retro` | Conduct a retrospective on a coding session. | https://github.com/mattpocock/skills |
| `setup-matt-pocock-skills` | Configure this repo for the engineering skills: set up its issue tracker, triage label vocabulary, and domain doc layout. Run once before first use of the other engineering skills. | https://github.com/mattpocock/skills |
| `setup-pre-commit` | Set up Husky pre-commit hooks with lint-staged (Prettier), type checking, and tests in the current repo. Use when user wants to add pre-commit hooks, set up Husky, configure lint-staged, or add commit-time formatting/typechecking/testing. | https://github.com/mattpocock/skills |
| `teach` | Teach the user a new skill or concept, within this workspace. | https://github.com/mattpocock/skills |
| `to-questionnaire` | Turn a decision you can't fully answer into a questionnaire for someone else to fill in. | https://github.com/mattpocock/skills |
| `to-spec` | Turn the current conversation into a spec and publish it to the project issue tracker: no interview, just synthesis of what you've already discussed. | https://github.com/mattpocock/skills |
| `to-tickets` | Break a plan, spec, or the current conversation into a set of tracer-bullet tickets, each declaring its blocking edges, published to the configured tracker (edges as text in one file per ticket locally, or native blocking links on a real tracker). | https://github.com/mattpocock/skills |
| `triage` | Move issues and external PRs through a state machine of triage roles, categorise, verify, grill if needed, and write agent-ready briefs. | https://github.com/mattpocock/skills |
| `ui-ux-pro-max` | UI/UX design intelligence. 67 styles, 161 palettes, 57 font pairings, 25 charts, 21 stacks (React, Next.js, Vue, Svelte, Astro, SwiftUI, React Native, Flutter, WPF, WinUI 3, UWP, Avalonia, Uno Platform, Nuxt, Nuxt UI, Tailwind, shadcn/ui, Jetpack Compose, Three.js, Angular, Laravel). Actions: plan, build, create, design, implement, review, fix, improve, optimize, enhance, refactor, check UI/UX code. Projects: website, landing page, dashboard, admin panel, e-commerce, SaaS, portfolio, blog, mobile app, desktop app, .html, .tsx, .vue, .svelte, .xaml. Elements: button, modal, navbar, sidebar, card, table, form, chart. Styles: glassmorphism, claymorphism, minimalism, brutalism, neumorphism, bento grid, dark mode, responsive, skeuomorphism, flat design. Topics: color palette, accessibility, animation, layout, typography, font pairing, spacing, hover, shadow, gradient. Integrations: shadcn/ui MCP for component search and examples. | local |
| `wait-what` | Stop. That last message did not land: re-pitch it. | https://github.com/mattpocock/skills |
| `wayfinder` | Plan a huge chunk of work (more than one agent session can hold) as a shared map of decision tickets on your issue tracker, and resolve them one at a time until the way to the destination is clear. | https://github.com/mattpocock/skills |
| `wizard` | Generate an interactive bash wizard that walks a human through steps only they can perform. Use when provisioning infrastructure, setting up credentials or CI secrets, walking an unfamiliar third-party dashboard, or running a one-off migration or cutover. Don't invoke this for steps the agent can perform itself. | https://github.com/mattpocock/skills |
| `writing-for-agents` | Writing documents for agents. Use when creating or editing skills, or modifying AGENTS.md or CLAUDE.md. | https://github.com/mattpocock/skills |

<!-- CATALOG:END -->
