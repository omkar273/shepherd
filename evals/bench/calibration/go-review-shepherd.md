# Draft review: `feat/void-invoices` → `main`

**Verdict:** request changes   **Lean:** about -40 lines   **Not checked:** I did not run `go build ./... && go vet ./...` or the tests on the branch tip. I did not run `capture.py lessons`, because the sandbox prompted for it. The PR has no title or body, so I judged scope from the diff.

## MUST

1. **`internal/worker/registration.go` (not in the diff): the void service is not wired into the worker.**
   - `AGENTS.md`: "A new service is constructed in `cmd/server/main.go` and in `internal/worker/registration.go`."
   - The PR adds `NewVoidService` only in `main.go`. `worker.Services` has only `Invoices`.
   - Fix: add a `Voids service.VoidService` field and build it in `Register`.
   - Combine this with finding 5, so that the constructor takes only `repo` and `tx`.

2. **`internal/api/invoice_handler.go:21` (`writeError`): `ErrAlreadyVoided` has no status mapping.**
   - `void.go:97` returns `ErrAlreadyVoided`. `writeError` only maps `ErrNotFound` and `ErrInvalidState`, so a double void returns 500 "internal error".
   - Fix: add `errors.Is(err, service.ErrAlreadyVoided)` to the `StatusConflict` case.

## SHOULD

3. **`internal/api/void_handler.go:25-28`: duplicate validation.**
   - The service already calls `req.Validate()` at `void.go:76`.
   - `AGENTS.md`: "Validation lives in the service." The handler copy runs the same check twice on the same path.
   - Fix: delete the handler copy. To keep the 400, map the service validation error to 400 in `writeError`.
   - The existing `Finalize` handler does not validate either.
   ```suggestion
   ```

4. **`internal/service/void.go:116-119`: log and return.**
   - `log.Printf` before `return nil, err` logs the error twice. `AGENTS.md`: "Log once, in the HTTP handler." `writeError` already logs.
   - Fix: delete the `log.Printf` line. Return `err` only.
   ```suggestion
   	if err := s.repo.Update(ctx, inv); err != nil {
   		return nil, err
   	}
   ```

5. **`internal/service/void.go:39-41,120-122`, `main.go:18`: `VoidOptions` is a stub.**
   - The only option, `NotifyCustomer`, only logs "would notify". The only caller passes `VoidOptions{}`, so the branch is dead.
   - Fix: delete `VoidOptions`, the field, the parameter, and the branch. Leave notification out until it exists.

6. **`internal/service/void.go:43-51,60,65,114`: `VoidReasonFormatter` has one implementation.**
   - There is one implementation (`defaultVoidReasonFormatter`) and no fake. Grep finds no other implementer.
   - It is not a service interface, so the repo convention does not cover it. It only wraps `strings.TrimSpace`.
   - Fix: delete the interface, the type, and the field. Use `inv.VoidReason = strings.TrimSpace(req.Reason)`.

7. **`internal/service/void.go:68-70,86`: `getInvoice` only forwards to `s.repo.Get`.**
   - Fix: inline `s.repo.Get(ctx, req.InvoiceID)`.

8. **`internal/service/void.go:73-75`: nil check on `s.repo`.**
   - `NewVoidService` is the only constructor, and it always sets `repo`. A nil repo is a wiring bug that main would hit at once.
   - Fix: delete the check.
   ```suggestion
   ```

9. **`internal/service/void.go:90-92`: nil check on `inv`.**
   - The contract at `domain/invoice.go:37` says `Get` returns `ErrNotFound` when the invoice is missing. It never returns `nil, nil`.
   - Fix: delete the check.
   - Keep the tenant and environment re-check at `void.go:93`. Defense in depth is on the never-cut list.
   ```suggestion
   ```

10. **`internal/service/void.go:104-108`: `len(inv.Lines) > 0` before `range`.**
    - Fix: delete the `if` and keep the loop.

11. **`internal/repository/memory/invoice.go:5,58`: unrelated change.**
    - The `sort.Slice` in `List` and the new import have nothing to do with voiding. No void code calls `List`.
    - Fix: remove the hunk. If the order matters, put it in its own PR.
    ```suggestion
    ```

12. **`internal/service/void.go:110`: comment `// void the invoice`.**
    - The code states this already. Delete it.

## ASK

13. **`internal/service/void.go:103-108,125`: what is `RefundCents`?**
    - No payment or refund data is read or written. The value is the sum of line amounts, whether or not the customer paid.
    - `Finalize` already stores `TotalCents` on the invoice.
    - Should the response return `inv.TotalCents`, or should `RefundCents` wait until refunds exist? The first option also removes the loop.

## Outside lean

- No tests for `Void`, and no `VoidService` fake for the handler. `AGENTS.md` says handler tests use fakes of the service interfaces. A not-found, already-voided, and invalid-state case would also cover finding 2.
- `Get` then `Update` has no version check, so two concurrent voids can both pass the state guard with a real DB. The memory repo hides this. Check it when a SQL repository lands. See `/code-review` for depth.

---

## Files read

Opened with Read:
- `plugin/code/review.md`
- `plugin/code/defensive.md`
- `plugin/lang/go.md`
- `plugin/ste.md`
- `repo/internal/worker/registration.go`
- `repo/internal/service/invoice.go`
- `repo/internal/api/invoice_handler.go`
- `repo/internal/domain/invoice.go`
- `repo/internal/repository/memory/invoice.go` (working tree, `main`)
- `repo/internal/api/invoice_handler_test.go`

Read through the `git diff main...feat/void-invoices` output (full diff, not opened as files):
- `cmd/server/main.go`
- `internal/api/void_handler.go`
- `internal/repository/memory/invoice.go`
- `internal/service/void.go`

Also used: `AGENTS.md` (provided in context, not opened with a tool) and the shepherd `SKILL.md` (loaded via the Skill tool).

I did not open `internal/types/context.go`.
