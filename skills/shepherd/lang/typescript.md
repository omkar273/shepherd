# TypeScript

Run the repo's lint and typecheck scripts (for example `lint`, `check-types`,
`ci` in `package.json`). In a monorepo, typecheck every package that depends on
the one you changed. If the repo has a dead-export tool (knip, ts-prune), run
it: a new unused export is a finding. Where the repo's lint config already
encodes a rule below, the linter is the authority.

## Idiomatic: keep

- Runtime parsing at boundaries with the repo's validator (zod, valibot):
  `req.json()`, `JSON.parse`, `fetch(...).json()`, env.
- `satisfies`.
- An exhaustive `switch` over a union with no `default`. When the union grows,
  add cases; never add a `default`.
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
  sites is fine; don't propose a shared helper for it.
- A type alias or function that only renames a library's type. Use the
  library's name.
- A static-only class, or module-level mutable state, where a factory with
  closure state is the repo's pattern.
- A type written out by hand that can be derived (`z.infer`, `Pick`,
  `ReturnType`).

## Boundaries: parse once, then trust

- Internal functions take the parsed type: no `unknown` or `any` parameters,
  no `typeof` re-checks, no `Record<string, unknown>`.
- Nothing downstream re-checks what the boundary schema guarantees. After
  `z.number().int().positive()`, a later `typeof x !== "number" || x <= 0` is
  noise.
- No `?.` or `??` on a value already narrowed. After `if (!x) throw ...`,
  `x?.y` is noise.
- `(await r.json()) as T` becomes a schema parse. No chained casts
  (`as A as B`) and no widen-then-assert.
- Failures are thrown or returned as a tagged result, never as a `T | string`
  message.

