## Draft review: `feat/apply-credit`

**Blocking**

1. `src/rpc/router.ts:8`: the procedure is never registered. No `CustomerStore` or `CreditService` is created either, so `applyCredit` is unreachable. Wire up `createCustomerStore`, `createCreditService` and register `applyCredit`.
2. `src/rpc/errors.ts:3`: `httpStatus` has no cases for `NO_CREDIT` or `CREDIT_EXCEEDS_TOTAL`. The switch returns `undefined` for them, which gives an undefined HTTP status and a type error. Add mappings, e.g. 409 or 422.
3. `src/billing/credit.ts:51`: the balance and invoice read-modify-write is not atomic.
   - Two concurrent calls can both read balance 100 and each spend 100 on different invoices.
   - If `invoices.save` succeeds and `setCreditBalance` fails, credit is applied without the balance being decremented.
   - Use a transaction or a conditional atomic update.

**Should fix**

4. `src/billing/credit.ts:31`: the `typeof` / positive check re-validates input that zod already parsed at the boundary. It also throws a bare `Error`, which maps to a 500, rather than a `BillingError`. Remove it.
5. `src/billing/credit.ts:52`: the try/catch only rethrows. Also:
   - `invoice?.totalCents` is redundant because `invoice` is already known non-null.
   - The `// apply the credit` comment violates "no comments".
   - The `getInvoice` and `isPositive` wrappers add nothing.
6. `src/billing/credit.ts:22`: `draft` invoices can receive credit; only `paid` is rejected. A fully credited invoice also never transitions to `paid`. Confirm the intended behaviour.
7. `web/InvoiceTotal.svelte:10`: use `$derived` instead of `$state` plus `$effect`. As written, Due renders `0.00` on first paint. `invoice` is also dereferenced in the script before the `{#if invoice}` guard.
8. `widgets/CreditBadge.tsx:8`: `useState(amountCents)` freezes the prop, so the badge goes stale when the amount changes. The label should be computed during render rather than via `useEffect`. The component is also not exported from `widgets/index.ts`.

**Also worth asking**: there are no tests for the credit service.

## Files read
- `src/rpc/errors.ts`
- `src/rpc/router.ts`
- `src/rpc/context.ts`
- `src/billing/store.ts`
- `widgets/index.ts`
- Diff content (via `git diff main...feat/apply-credit`): `src/billing/credit.ts`, `src/billing/errors.ts`, `src/rpc/procedures/apply-credit.ts`, `web/InvoiceTotal.svelte`, `widgets/CreditBadge.tsx`

Findings, one line each:
- `src/rpc/router.ts:8` — applyCredit procedure not registered, no credit service wired
- `src/rpc/errors.ts:3` — no HTTP status for NO_CREDIT / CREDIT_EXCEEDS_TOTAL
- `src/billing/credit.ts:51` — non-atomic balance and invoice update, race and partial failure
- `src/billing/credit.ts:31` — redundant validation throwing a plain Error
- `src/billing/credit.ts:52` — useless try/catch, comment, redundant `?.` and wrappers
- `src/billing/credit.ts:22` — draft allowed, full credit doesn't mark paid
- `web/InvoiceTotal.svelte:10` — derived state via `$effect`, deref before guard
- `widgets/CreditBadge.tsx:8` — frozen prop state, derived label via effect, not exported from index

Note: I briefly ran `git checkout` to read the branch's files and returned to `main`. The working tree is unchanged.

Findings reported with the ReportFindings tool:
[
 {
  "findings": [
   {
    "file": "src/rpc/router.ts",
    "line": 8,
    "summary": "applyCreditProcedure is never registered in the router, and no CreditService/CustomerStore is created.",
    "failure_scenario": "The procedure is unreachable per AGENTS.md; clients calling applyCredit get nothing. The router must create createCustomerStore and createCreditService and register applyCredit.",
    "verdict": "CONFIRMED"
   },
   {
    "file": "src/rpc/errors.ts",
    "line": 3,
    "summary": "httpStatus has no cases for the new NO_CREDIT and CREDIT_EXCEEDS_TOTAL codes.",
    "failure_scenario": "Throwing NO_CREDIT makes httpStatus return undefined (and fails type-check for non-exhaustive switch), so the response has an undefined status instead of e.g. 409/422.",
    "verdict": "CONFIRMED"
   },
   {
    "file": "src/billing/credit.ts",
    "line": 51,
    "summary": "Read-modify-write on balance and invoice with no transaction or atomic update; the two saves are non-atomic.",
    "failure_scenario": "Two concurrent applyCredit calls both read balance 100 and apply 100 to different invoices, so the customer spends 200 credit and the balance is set to 0. Also if invoices.save succeeds and setCreditBalance fails, the invoice is credited but the balance is not decremented (credit applied twice-free).",
    "verdict": "CONFIRMED"
   },
   {
    "file": "src/billing/credit.ts",
    "line": 31,
    "summary": "Redundant re-validation of amountCents and a plain Error thrown from domain code.",
    "failure_scenario": "The rpc boundary already parses with zod (int, positive); the internal check duplicates it and throws a bare Error, which toHttpError maps to 500 rather than a BillingError code, contrary to AGENTS.md.",
    "verdict": "CONFIRMED"
   },
   {
    "file": "src/billing/credit.ts",
    "line": 52,
    "summary": "Useless try/catch that only rethrows; also stray `invoice?.` on a value already known non-null, an `// apply the credit` comment (repo bans comments), and pointless getInvoice/isPositive wrappers.",
    "failure_scenario": "No behavioral failure, but violates the 'No comments' and 'handlers do not catch' conventions and adds noise.",
    "verdict": "CONFIRMED"
   },
   {
    "file": "src/billing/credit.ts",
    "line": 22,
    "summary": "Invoice with status \"draft\" is allowed to receive credit; only \"paid\" is rejected. Also invoice becomes fully covered (remaining 0) but status is never set to paid.",
    "failure_scenario": "Applying credit equal to the full remaining amount leaves status \"open\" with zero due, and a later call is rejected only by CREDIT_EXCEEDS_TOTAL; draft invoices can be credited before finalization.",
    "verdict": "PLAUSIBLE"
   },
   {
    "file": "web/InvoiceTotal.svelte",
    "line": 10,
    "summary": "Derived value is held in $state updated by $effect, and `invoice` is dereferenced before the `{#if invoice}` guard.",
    "failure_scenario": "Use $derived instead; the effect runs after first render so Due shows 0.00 initially, and if invoice is undefined the effect throws before the guard matters.",
    "verdict": "CONFIRMED"
   },
   {
    "file": "widgets/CreditBadge.tsx",
    "line": 8,
    "summary": "useState(amountCents) freezes the prop on first render; label is derived state via useEffect; and the widget is not exported through widgets/index.ts.",
    "failure_scenario": "After a credit is applied and the parent passes a new amountCents, the badge keeps showing the old amount. Consumers cannot import it via widgets/index.ts as required.",
    "verdict": "CONFIRMED"
   }
  ],
  "level": "medium"
 }
]
