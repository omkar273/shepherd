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

Run the tools first. A tool finding is the authority. Do not repeat a rule
here that a tool already reports.

1. The repo's typecheck: a `typecheck`, `check-types`, or `check` script, or
   `tsc --noEmit` if `typescript` is in `package.json`. In a monorepo,
   typecheck each package that depends on the changed package.
2. The repo's eslint or biome script. If the config turns on
   `no-useless-catch`, `@typescript-eslint/no-unnecessary-condition`, or
   `@typescript-eslint/no-floating-promises`, trust the tool for those rules.
3. A dead-export tool (knip, ts-prune) if the repo has one. A new unused
   export is a finding.

Use only the tools in the repo's `package.json`. Do not install a tool.

Impact: CRITICAL is a security, money, or data bug, or a feature that does
not work. HIGH is a bug in some cases, a failure that nobody sees, or a slow
path. MEDIUM is code that adds nothing. Fix or flag the CRITICAL items first.

## Keep

- **CRITICAL.** Owner, tenant, and state checks in a service, also when the
  caller checks too. See the never-cut list.
  ```ts
  if (order.accountId !== ctx.accountId) throw new OrderError("NOT_FOUND") // keep
  ```
- **CRITICAL.** An exhaustive `switch` over a union, with no `default`. When
  the union grows, add cases. With a `default`, a new code becomes a 500 and
  tsc stays quiet.
  ```ts
  default: return 500                // bad: hides each new code
  case "OUT_OF_STOCK": return 409   // good: tsc fails until each code has a case
  ```
- **HIGH.** A runtime parse at each boundary with the repo's validator (zod,
  valibot): `req.json()`, `JSON.parse`, `fetch(...).json()`, env.
  ```ts
  const body = (await res.json()) as Order // bad: a cast is not a check
  const body = Order.parse(await res.json()) // good
  ```
- **HIGH.** `await` on each promise, or one `.catch` on a fire-and-forget
  call. A floating promise loses its error.
  ```ts
  audit.record(event)                 // bad: rejection goes nowhere
  void audit.record(event).catch(log) // good
  ```
- **HIGH.** `?.` and `??` on a value whose type is really optional. If a
  default hides missing money or quantity data, ask about it. Do not cut it.
  ```ts
  const city = user!.address.city           // bad: address is optional
  const city = user.address?.city ?? "-"     // good
  ```
- **MEDIUM.** `satisfies`, `AbortSignal.timeout`, `AbortSignal.any`, and
  `try`/`finally` cleanup.

## Cut

- **HIGH.** Sequential `await`s on independent calls. Start them together.
  ```ts
  const user = await getUser(id); const cart = await getCart(id) // bad
  const [user, cart] = await Promise.all([getUser(id), getCart(id)]) // good
  ```
- **MEDIUM.** When you write a conditional update, do not also read and
  check the same rule before it. The update is the check. If it changes no
  row, throw. This rule is for code that you write. In a review, keep each
  money check, and do not tell the author to remove one.
  ```ts
  if ((await accounts.get(id)).balance < cents) throw new AccountError("LOW") // bad
  if (!(await accounts.debit(id, cents))) throw new AccountError("LOW") // good: where balance >= $1
  ```
- **MEDIUM.** A pass-through function. Call the target directly.
  ```ts
  const getOrder = async (id: string) => await store.get(id) // bad
  ```
- **MEDIUM.** A one-expression helper with one or two callers that names no
  domain concept. Write the expression inline.
- **MEDIUM.** Error factories (`function notFound(id) { return new XError() }`),
  throw-only `assertX` helpers, catch-only helpers, and error-message helpers.
  The same `new XError(...)` at two throw sites is fine.
- **MEDIUM.** A catch that only throws again.
  ```ts
  try { await save(o) } catch (e) { throw e } // bad
  await save(o)                               // good
  ```
- **MEDIUM.** A new interface with one implementation and no fake, outside
  the repo's convention. If the repo's services use a `createX` factory that
  returns interface `X`, the interface is the convention. Keep it. Grep the
  other services and the tests before you flag one.
- **MEDIUM.** A type alias or function that only renames a library's type,
  and a hand-written type that you can derive (`z.infer`, `Pick`,
  `ReturnType`).
- **MEDIUM.** A static-only class, or module-level mutable state, where a
  factory with closure state is the repo's pattern.
- **MEDIUM.** A wait on a timer. Wait on the event, promise, or signal.

## Boundaries

Parse once at the boundary. After that, trust the parsed type.

- Internal functions take the parsed type. Do not use `unknown` or `any`
  parameters, `typeof` re-checks, or `Record<string, unknown>` in them.
- Do not check again what the boundary schema guarantees. Do not use `?.` or
  `??` on a value that the code already narrowed.
  ```ts
  const input = z.object({ qty: z.number().int().positive() }).parse(raw)
  if (typeof input.qty !== "number" || input.qty <= 0) throw ... // bad
  ```
- Do not use chained casts (`as A as B`) or widen-then-assert.
- Throw a failure, or return it as a tagged result. Never return a failure
  as a `T | string` message.
- Map domain errors to transport errors in one boundary layer. Do not wrap
  calls in try/catch in handlers or internal functions.

## Wiring

- **CRITICAL.** Register each new procedure or route in the router. A
  procedure that no router lists is unreachable.
  ```ts
  export const router = { getOrder }            // bad: shipOrder is missing
  export const router = { getOrder, shipOrder } // good
  ```
- **CRITICAL.** Add each new error code to the error-to-status mapping.
  ```ts
  // bad: "OUT_OF_STOCK" has no case, so the client gets a 500
  case "OUT_OF_STOCK": return 409 // good
  ```
- **HIGH.** Generated files (route trees, API clients): regenerate them.
  Never edit them by hand.
  ```sh
  $EDITOR src/routeTree.gen.ts  # bad: the next build drops the edit
  npm run generate              # good: use the repo's script
  ```
- **MEDIUM.** The consumer's `package.json` workspace dependency, and the
  package's `exports` or barrel `index.ts` if the repo routes imports through
  it.
- **MEDIUM.** Env vars, wherever the repo declares them: an example env file,
  turbo `globalEnv`, or a config schema.
