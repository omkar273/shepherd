## Review of `feat/refunds`

I read the diff and the full branch versions of `http.py`, `models.py`, `repo.py` and `service.py`. I did not run the tests.

### Blocking

**1. `handle_refund` is not in `ROUTES`** (`billing/http.py`, around the `ROUTES` dict)
The handler is never registered, so `POST invoice/refund` returns `404 no route`. Per AGENTS.md, a handler is reachable only from `ROUTES`. The feature doesn't work over HTTP as written. Please add `("POST", "invoice/refund"): handle_refund`, and add an HTTP-level test, since the new tests only call the service directly.

**2. `RefundTooLarge` has no entry in `ERROR_STATUS`** (`billing/http.py:10`)
`dispatch` falls back to `ERROR_STATUS.get(type(exc), 500)`. An over-refund will return a 500 for what is a client error. AGENTS.md requires every domain error to have a status. Suggest 409 or 422, whichever fits your API conventions. Add a test for it.

**3. The service re-validates a request the HTTP layer already parsed** (`billing/service.py`, `refund`, first `if`)
`parse_refund` already checks that `amount_cents` is a positive int. AGENTS.md says services take parsed values and don't check them again. Drop the `isinstance` / `<= 0` check and its `InvalidRequest`. The `void` method has a similar length check, but that is existing code and not a reason to add more.

### Should fix

**4. Redundant `service.get(ctx, invoice_id)` in `handle_refund`** (`billing/http.py`)
The result is discarded, and `refund` already does the existence and tenant check under the lock. It's a wasted lookup. In `handle_void` it exists only to capture `previous`, which doesn't apply here.

**5. Duplicated lookup and tenant check, plus a dead `_get_invoice` helper** (`billing/service.py`)
- `_get_invoice` is a one-line passthrough to `repo.get`.
- `repo.get` raises `NotFound` and never returns `None`, so the `if invoice is None: raise NotFound` branch is dead code.
- `self.get(ctx, invoice_id)` already does the lookup and tenant check, and `pay` uses it inside the lock. Use that and delete `_get_invoice`, the `None` check and the tenant check.

**6. `try: ... except Exception: raise` is a no-op** (`billing/service.py`, end of `refund`)
Remove it and dedent the body.

**7. The `notify` parameter is unused scaffolding** (`billing/service.py`)
- Nothing passes it, and the only effect is a log line saying "would notify".
- AGENTS.md says to log once, in `http.py`, so this `log.info` in the service also breaks that rule.
- It also adds a module-level `log` to `service.py`.
- Remove `notify`, `logging` and `log`, or implement notification properly in a separate PR.

**8. `RefundPolicy` ABC and `DefaultRefundPolicy` are speculative abstraction** (`billing/refund_policy.py`, `InvoiceService.__init__`)
- There is one implementation, one method, and no caller that injects another.
- It adds a new module and a new constructor argument on `InvoiceService`.
- A `max_refund = paid_cents - refunded_cents` check inline would do. Introduce the abstraction when a second policy appears.
- `policy.max_refund(invoice)` is also called twice, once for the check and once for the message. Store it in a local variable if you keep it.

**9. Unrelated change to `fmt_cents`** (`billing/money.py`)
`divmod` plus `%` formatting replaces an f-string and is equivalent for the values that matter here, so it adds noise to the diff and is stylistically a step backwards. Please revert it, or explain why it's needed. (If the intent was to handle negatives, say so, as the old code was equally wrong there.)

### Nits / tests

- **10.** The comment `# refund the invoice` just restates the code. Remove it.
- **11.** Tests are missing for:
  - a refund over the remaining amount (`RefundTooLarge`);
  - a refund on a non-paid invoice (409);
  - a cross-tenant refund (404);
  - a cumulative refund that goes over the limit;
  - the HTTP path (`parse_refund` rejections: bool, zero, missing `request_id`).
- **12.** Behaviour question: an idempotent replay returns the invoice before the status check, which is good. But a replay with the same `request_id` and a *different* amount silently succeeds. Consider whether that should be an error.
- **13.** After a full refund the invoice stays `PAID` with `refunded == paid`. If that's intended, fine, but it's worth confirming.

### Files read
- `billing/errors.py` (via the diff)
- `billing/http.py` (full, branch version)
- `billing/money.py` (via the diff)
- `billing/refund_policy.py` (via the diff)
- `billing/service.py` (diff plus the top 50 lines of the branch version)
- `billing/models.py` (branch version)
- `billing/repo.py` (branch version)
- `tests/test_billing.py` (via the diff only)
- `AGENTS.md` (supplied in context)
