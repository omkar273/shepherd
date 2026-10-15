# Draft review: `feat/refunds` → `main`

One commit (`255b879`). I did not run the test suite, and nothing was posted or modified. Main-branch files were read through `git show` on the branch, with no checkout left behind.

## Blocking

**1. `handle_refund` is not registered in `ROUTES`, so refunds are unreachable** (`billing/http.py`, the `ROUTES` dict)

`dispatch` only looks handlers up in `ROUTES`, and the PR adds `handle_refund` and `parse_refund` without an entry. Every refund request returns `404 {"error": "no route"}`.

AGENTS.md: "A handler is reachable only from `ROUTES` in `billing/http.py`."

Suggested fix:
```python
("POST", "invoice/refund"): handle_refund,
```
Please add an HTTP-level test through `dispatch`. Both new tests call the service directly, which is why this slipped through.

**2. `RefundTooLarge` has no entry in `ERROR_STATUS`, so over-refunds return 500** (`billing/errors.py`, `billing/http.py:11-15`)

`dispatch` uses `ERROR_STATUS.get(type(exc), 500)`, and the lookup is by exact type. An over-refund is a client error but would be reported as a server error.

AGENTS.md: "Every domain error has a status in `ERROR_STATUS` in `billing/http.py`."

Suggested fix: add `RefundTooLarge: 409` (or 422) to `ERROR_STATUS`, and cover it with a test.

**3. The service logs, and re-validates input the HTTP layer already parsed** (`billing/service.py`, `refund`)

- `log.info("would notify customer …")` and the module-level `log` add logging in the service. AGENTS.md: "Log once, in `billing/http.py`."
- `if not isinstance(amount_cents, int) or amount_cents <= 0: raise InvalidRequest(...)` repeats the check in `parse_refund`. AGENTS.md: "`billing/http.py` parses each request body once (`parse_*`). Services take the parsed values and do not check them again."
  - Other service methods validate (for example `void` checks `reason`), so there is precedent. That precedent predates the rule, though, and the rule is explicit.
  - The service check is also weaker than `parse_refund`, because it accepts `bool`.

Suggested fix: drop both from the service.

## Should fix

**4. Speculative or dead code in `refund`** (`billing/service.py`)

- `notify: bool = False` is never passed by anyone and only logs "would notify". Remove the parameter and the branch.
- `except Exception: raise` is a no-op. Remove it and the `try`.
- `_get_invoice` is a one-line wrapper over `repo.get`, and `repo.get` raises `NotFound` and never returns `None`. The `if invoice is None` branch is dead. Use `self.get(ctx, invoice_id)` inside the lock, as `pay` does. That also covers the tenant check and removes the duplicated `tenant_id` comparison.
- `self.policy.max_refund(invoice)` is called twice. Compute it once.
- `RefundPolicy` (ABC) plus `DefaultRefundPolicy` is a new module and an injection point for a single implementation that returns `paid - refunded`. Inline it unless a second policy is actually planned.
- The `# refund the invoice` comment restates the code.

**5. Redundant `service.get(ctx, invoice_id)` in `handle_refund`** (`billing/http.py`)

The result is discarded. `void` needs it to capture `previous`, but refund has no such need, and `refund` already does the tenant and not-found checks under the lock. Remove it.

## Nits

- `billing/money.py`: the `fmt_cents` rewrite is unrelated to refunds and behaves identically. `divmod` gives the same result as `//` and `%`. Drop it from this PR, or if it is intentional, use an f-string to match the old style.
- Test gaps: there is no test for the too-large path, a refund on a non-PAID invoice, a cross-tenant refund, or the HTTP path (which would have caught items 1 and 2).

## Files read

- `AGENTS.md` (provided in the session context; not opened separately)
- `billing/http.py` (branch version)
- `billing/models.py` (branch version)
- `billing/repo.py` (branch version)
- `billing/service.py` (branch version)
- `billing/worker.py` (branch version)
- Seen only as diff hunks from `git diff main...feat/refunds`, not opened in full: `billing/errors.py`, `billing/money.py`, `billing/refund_policy.py`, `tests/test_billing.py`
