# app

- Factories, not classes: `createX` returns an interface `X`. Classes only for
  `extends Error`.
- Parse unknown input once at the rpc boundary with zod. Internal code takes
  the parsed type and does not re-check it.
- Domain code throws `BillingError` with a `code`. `src/rpc/errors.ts` maps
  every code to an HTTP status; handlers do not catch.
- A procedure is reachable only once `src/rpc/router.ts` registers it.
- Widgets are used through `widgets/index.ts`.
- No comments in code.
- Svelte 5 runes in `web/`, React in `widgets/`.
