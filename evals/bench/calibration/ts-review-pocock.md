# Review: `feat/apply-credit`

## Blocking

**1. Procedure is never registered, so the feature is unreachable.** `src/rpc/router.ts`
`applyCreditProcedure` exists, but `createRouter` doesn't register it. It also needs `createCustomerStore` and `createCreditService` wired in. AGENTS.md: "A procedure is reachable only once `src/rpc/router.ts` registers it."

**2. New error codes aren't mapped to HTTP statuses.** `src/rpc/errors.ts`
`httpStatus` has no cases for `NO_CREDIT` or `CREDIT_EXCEEDS_TOTAL`. Nothing in this PR touches that file. The switch returns `undefined` for these codes, so `toHttpError` returns `status: undefined`. AGENTS.md requires every code to be mapped (suggest 409 or 422).

**3. Plain `Error` thrown from domain code.** `src/billing/credit.ts`, the `amountCents` guard
`throw new Error("amountCents must be a positive number")` will surface as a 500. Domain code must throw `BillingError` with a code. The check is also redundant: zod already enforces `.int().positive()` at the rpc boundary, and AGENTS.md says internal code doesn't re-check parsed input. Remove it, along with the `isPositive` helper and the `typeof` check.

**4. Non-atomic write can corrupt balances and allow double-spend.** `src/billing/credit.ts`, the save and `setCreditBalance` calls
- `invoices.save` and `customers.setCreditBalance` are two separate writes. If the second fails, the invoice is credited but the customer balance isn't debited.
- Concurrent requests both read the same balance and invoice, then overwrite each other. This is a read-modify-write race, so the same credit can be spent twice.
- This needs a transaction, or an atomic conditional update such as `set credit_balance_cents = credit_balance_cents - $1 where ... and credit_balance_cents >= $1`.

## Should fix

**5. Dead and incorrect code in `credit.ts`.**
- `try { ... } catch (error) { throw error; }` does nothing. Remove it.
- `invoice?.totalCents` is inconsistent: `invoice` is already narrowed non-undefined, and the other accesses don't use `?.`.
- The `// apply the credit` comment violates "No comments in code".
- `getInvoice` is a pointless wrapper around `invoices.get`.
- `notFound` duplicates `BillingService.getInvoice`'s not-found handling. Reuse `billing.getInvoice` (as `get-invoice.ts` does) instead of re-implementing it.
- The customer-ownership check (`customerId !== input.customerId`) is duplicated from `get-invoice.ts`. Consider centralizing it.

**6. Missing customer is silently treated as zero balance.** `customer?.creditBalanceCents ?? 0` reports `NO_CREDIT` for a nonexistent customer. That's probably fine, but it should be a deliberate choice, and a missing customer is more naturally `NOT_FOUND`.

**7. Draft invoices can receive credit.** Only `paid` is rejected. Confirm that crediting a `draft` invoice is intended.

**8. Check order leaks information.** The balance is checked before the amount-due check. This is minor, but checking the invoice-level constraint first is more natural.

## Frontend

**9. `web/InvoiceTotal.svelte`: `$state` + `$effect` for derived value.** Use `const due = $derived(invoice.totalCents - invoice.creditAppliedCents)`. The effect causes an extra render pass and is the wrong rune for this. Also:
- `{#if invoice}` is pointless, because `invoice` is a required prop and is already dereferenced unconditionally in the script above.
- The `due` computation would throw before the guard anyway.

**10. `widgets/CreditBadge.tsx`: needless state.**
- `useState(amountCents)` freezes the initial prop, so the badge goes stale when the prop changes.
- `label` is derived state set in an effect, which causes a flash of an empty badge on first render. `useMemo` for `amount > 0` is also unnecessary.
- Compute it directly: `if (amountCents <= 0) return null; return <span className="badge">${(amountCents/100).toFixed(2)} credit</span>`.

**11. Widget not exported through `widgets/index.ts`.** AGENTS.md says widgets are used through the index. Add `export { CreditBadge } from "./CreditBadge";`.

## Other

- No tests are included for the credit logic (over-credit, paid invoice, wrong customer, concurrency).

## Files read

- `AGENTS.md` (provided in context)
- `src/billing/credit.ts` (via diff)
- `src/billing/errors.ts` (via diff)
- `src/rpc/procedures/apply-credit.ts` (via diff)
- `web/InvoiceTotal.svelte` (via diff)
- `widgets/CreditBadge.tsx` (via diff)
- `src/rpc/errors.ts`
- `src/rpc/router.ts`
- `widgets/index.ts`
- `src/billing/store.ts`
- `src/rpc/context.ts`
- `src/rpc/procedures/get-invoice.ts`
- `src/billing/service.ts`
