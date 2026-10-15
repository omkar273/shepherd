# Draft review: `feat/refunds` → `main`

```text
Verdict: request changes   Lean: about -35 lines   Not checked: I did not run `python3 -m unittest`. I did not review the tests beyond the two new refund cases.
```

## MUST

**1. `billing/http.py:64`: `handle_refund` is not in `ROUTES`.**
- Evidence: `AGENTS.md` says "A handler is reachable only from `ROUTES`". The diff does not touch `ROUTES`, so `dispatch` returns 404 `no route` for every refund request.
- Fix: add `("POST", "invoice/refund"): handle_refund,` to `ROUTES`.

**2. `billing/http.py:9`: `RefundTooLarge` is not in `ERROR_STATUS`.**
- Evidence: `AGENTS.md` says "Every domain error has a status in `ERROR_STATUS`". `dispatch` uses `ERROR_STATUS.get(type(exc), 500)`, so an over-limit refund returns 500.
- Fix: add `RefundTooLarge: 409` (or `422`, your choice) to `ERROR_STATUS`, and import it.

## SHOULD

**3. `billing/refund_policy.py:1`: abstract class with one implementation.**
- Evidence: `RefundPolicy` has one subclass, `DefaultRefundPolicy`. Nothing else passes `policy` to `InvoiceService`. `max_refund` is also called twice in `refund`.
- Fix: delete the file and the `policy` argument. Use a local in `refund`:

```python
left = invoice.paid_cents - invoice.refunded_cents
if amount_cents > left:
    raise RefundTooLarge(f"refund exceeds the {left} cents left")
```

**4. `billing/service.py:53`: the amount is checked again in the service.**
- Evidence: `AGENTS.md` says "`billing/http.py` parses each request body once (`parse_*`). Services take the parsed values and do not check them again." `parse_refund` (`http.py:24`) already rejects non-int, bool, and `<= 0`. The only caller is `handle_refund`.
- Fix: delete lines 53–54.

```suggestion
```

**5. `billing/service.py:75`: `except Exception: raise` does nothing.**
- Evidence: it only re-raises. The `try:` at line 55 is also not needed.
- Fix: remove the `try` and the `except`, and de-indent the `with` block.

**6. `billing/service.py:48`: `_get_invoice` only forwards to `repo.get`, and the `None` check is dead.**
- Evidence: `InvoiceRepo.get` raises `NotFound` and never returns `None` (`repo.py:15`). So lines 58–59 cannot run. The tenant check at line 60 repeats `InvoiceService.get`.
- Fix: delete `_get_invoice`. Use `invoice = self.get(ctx, invoice_id)` inside the lock, as `pay` does. Delete lines 58–61.

**7. `billing/service.py:72`: the `notify` flag is a stub.**
- Evidence: no caller passes `notify`. The branch only logs "would notify". `AGENTS.md` says "Log once, in `billing/http.py`", so the `log` in `service.py` breaks that rule.
- Fix: delete the `notify` parameter, the `if notify:` block, `import logging`, and `log`.

**8. `billing/http.py:60`: the result of `service.get(...)` is not used.**
- Evidence: `refund` already does the tenant check and raises `NotFound`. In `handle_void` the `get` is used to read `previous`. Here nothing reads it.
- Fix: delete the line.

**9. `billing/money.py:2`: unrelated change.**
- Evidence: `divmod` and `%` formatting give the same output as the old f-string for all ints. The PR intent is refunds.
- Fix: revert this file.

**10. `billing/service.py:68`: the comment `# refund the invoice` repeats the code.**
- Fix: delete it.

## ASK

None.

## Outside lean

- `tests/test_billing.py`: there is no test for `RefundTooLarge`, for a wrong tenant, or for a refund on an unpaid invoice. A test of the HTTP path through `dispatch` would have caught findings 1 and 2. Run `/code-review` for depth.

## Files read

Opened with Read or `git show` / `git diff` at `feat/refunds` (base `main`):
- `plugin/code/review.md`
- `plugin/code/defensive.md`
- `plugin/ste.md`
- `billing/http.py`
- `billing/models.py`
- `billing/repo.py`
- `billing/worker.py`
- `billing/service.py` (the first 50 lines, plus the diff)
- Diff only: `billing/errors.py`, `billing/money.py`, `billing/refund_policy.py`, `tests/test_billing.py`

Also in context, not opened by me:
- `AGENTS.md` (supplied in the session context)
- `plugin/SKILL.md` (loaded by the skill)

I ran `plugin/hooks/capture.py lessons`. It printed no lessons.
