## Draft review of `feat/apply-credit`

**Blocking**

1. **`src/rpc/router.ts`: the procedure is never registered.** `applyCreditProcedure` is unreachable until it's added to `createRouter`. That also needs a `createCustomerStore({ db })` and `createCreditService({ invoices, customers })` wired up there (the router currently builds only `invoices` and `billing`).

2. **`src/rpc/errors.ts`: `NO_CREDIT` and `CREDIT_EXCEEDS_TOTAL` have no HTTP status.** `httpStatus` has no `default`, so the switch returns `undefined` for the new codes and the response status is broken. Map them, for example `NO_CREDIT` to 409 or 422 and `CREDIT_EXCEEDS_TOTAL` to 422.

3. **`src/billing/credit.ts`: a plain `Error` is thrown for bad input.** `throw new Error("amountCents must be a positive number")` would surface as a 500. It is also a re-check of something zod already guarantees (`.int().positive()` in the procedure). Per AGENTS.md, internal code shouldn't re-validate parsed input, so remove the `typeof`/`isPositive` check along with the `isPositive` helper.

4. **`src/billing/credit.ts`: the two writes aren't atomic.** If `invoices.save` succeeds and `setCreditBalance` fails, the invoice shows credit applied but the customer's balance is untouched, so the credit can be reused. The balance is also read-then-written, so two concurrent requests can both pass the `balance` check and overspend. Use a transaction with a conditional update (`... where credit_balance_cents >= $1`), or at minimum a row lock.

5. **`src/billing/credit.ts`: `remaining` has a stray `?.`.** `invoice?.totalCents` is inconsistent, because `invoice` is already narrowed to non-null at that point. Drop the `?.`.

**Should fix**

6. **`src/billing/credit.ts`: remove the redundant wrapper, comment and `try/catch`.**
   - `getInvoice` just forwards to `invoices.get`.
   - `catch (error) { throw error; }` is a no-op.
   - `// apply the credit` breaks the "no comments" rule.
   - The duplicate `notFound` branches can merge into `if (!invoice || invoice.customerId !== input.customerId)`.

7. **`src/billing/credit.ts`: the `draft` status isn't handled.** Only `paid` is rejected, so credit can be applied to draft invoices. Confirm that's intended.

8. **`src/billing/credit.ts`: the `NOT_FOUND` message for a missing customer is inaccurate.** A missing customer silently becomes a balance of 0 and then `NO_CREDIT`. That is probably fine, but note it.

9. **`widgets/CreditBadge.tsx`: the props are copied into state.**
   - `useState(amountCents)` ignores later prop changes, so the badge goes stale.
   - `label` held in state plus an effect is derived state and causes an extra render.
   - Compute directly: `if (amountCents <= 0) return null; return <span className="badge">{`$${(amountCents / 100).toFixed(2)} credit`}</span>;`
   - Drop `useMemo`, `useEffect` and `useState`.

10. **`widgets/index.ts`: `CreditBadge` isn't exported.** Widgets are used through the index, so add `export { CreditBadge } from "./CreditBadge";`.

11. **`web/InvoiceTotal.svelte`: `$state` plus `$effect` for derived values.** Use `const due = $derived(invoice.totalCents - invoice.creditAppliedCents)`. The `{#if invoice}` guard is also inconsistent: the script already dereferences `invoice` unconditionally, and the prop is typed non-null.

**Nits / tests**

12. There are no tests for any of the new paths (credit exceeds balance, exceeds due, wrong customer, paid invoice, and the partial-failure case).

13. `applyCreditProcedure` takes `{ credits }`, but the router names its service `billing`. Keep the naming consistent once it's wired up.

## Files read

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

I also listed the `src/rpc/procedures` directory but did not open any other files in it.
