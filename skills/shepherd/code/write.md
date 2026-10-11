# Write mode

## 1. Map before writing code

- Trace the path the change touches: entry point, handler, service,
  store or external call, response. Read it; don't infer it.
- Write the reach list: every place the change must land.
  - Callers of anything whose signature or behavior changes.
  - Registrations: routes, router tables, DI containers, worker or job setup,
    exports and barrel files.
  - Error-to-status mappings for every new error value.
  - Config and env, including the example env file.
  - Migrations, and generated code (regenerate it, never hand-edit it).
  - Tests, only where the repo's test policy asks for them.
- Pick the rung from the ladder in `SKILL.md`.
- Before calling an API, read its signature in the source or in the installed
  version. Before using a CLI flag, check `--help`.
- Fix a bug once, in the shared code, not in one caller.

