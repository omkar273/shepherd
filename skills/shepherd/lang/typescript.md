---
paths:
  - "**/*.ts"
  - "**/*.tsx"
  - "**/*.mts"
  - "**/*.cts"
  - "**/*.jsx"
  - "**/*.svelte"
---

# TypeScript

Run the repo's lint and typecheck scripts (for example `lint`, `check-types`,
`ci` in `package.json`). In a monorepo, typecheck every package that depends
on the package that you changed. If the repo has a dead-export tool (knip,
ts-prune), run it. A new unused export is a finding. If the repo's lint config
already encodes a rule below, the linter is the authority.

## Idiomatic: keep

- Runtime parsing at boundaries with the repo's validator (zod, valibot):
  `req.json()`, `JSON.parse`, `fetch(...).json()`, env.
- `satisfies`.
- An exhaustive `switch` over a union with no `default`. When the union grows,
  add cases, and never add a `default`.
- `?.` and `??` on values whose type really is optional.
- `AbortSignal.timeout`, `AbortSignal.any`, `try`/`finally` cleanup.

## Shape: cut

- Pass-through functions: `const get = async (id) => await store.get(id)`.
  Call `store.get` directly.
- A one-expression helper with one or two callers that names no domain
  concept. Write the expression inline.
- Error factories (`function notFound(id) { return new XError(...) }`),
  throw-only `assertX` helpers, catch-only helpers, error-message helpers
  (`String(error)` already does it). The same `new XError(...)` at two throw
  sites is fine. Do not propose a shared helper for it.
- A type alias or function that only renames a library's type. Use the
  library's name.
- A static-only class, or module-level mutable state, where a factory with
  closure state is the repo's pattern.
- A hand-written type that you can derive (`z.infer`, `Pick`, `ReturnType`).

## Boundaries: parse once, then trust

- Internal functions must take the parsed type. Do not use `unknown` or `any`
  parameters, `typeof` re-checks, or `Record<string, unknown>` in them.
- Do not re-check downstream what the boundary schema guarantees. After
  `z.number().int().positive()`, a later `typeof x !== "number" || x <= 0` is
  noise.
- Do not use `?.` or `??` on a value that the code already narrowed. After
  `if (!x) throw ...`, `x?.y` is noise.
- Replace `(await r.json()) as T` with a schema parse. Do not use chained
  casts (`as A as B`) or widen-then-assert.
- Throw a failure, or return it as a tagged result. Never return a failure as
  a `T | string` message.

## Errors and async

- Map domain errors to transport errors in one boundary layer. Do not wrap
  calls in try/catch in handlers or internal functions. Always cut
  `catch (e) { throw e }`.
- Use `await` inside `try`, not promise chains. Write fire-and-forget as one
  statement: `task().catch(log)`.
- Wait on the event, promise, or signal, never on a timer.

## Wiring

- Register each new procedure or route in the router. Add each new error code
  to the error-to-status mapping.
- The consumer's `package.json` workspace dependency, and the package's
  `exports` or barrel `index.ts` if the repo routes imports through it.
- Declare env vars wherever the repo declares them (an example env file, turbo
  `globalEnv`, a config schema).
- Generated files (route trees, API clients): regenerate them. Never hand-edit
  them.
