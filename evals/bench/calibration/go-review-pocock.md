# Review of `feat/void-invoices` → `main`

I did not build or run anything; this is from reading the diff and surrounding code.

## Must fix

**1. `ErrAlreadyVoided` returns 500 to the client** — `internal/service/void.go:14`, `internal/api/invoice_handler.go` (`writeError`)
`writeError` only maps `ErrNotFound` and `ErrInvalidState`. `ErrAlreadyVoided` falls to `default` and returns 500 "internal error". A double-void is a client conflict, so it should be 409. Either add a `case` in `writeError`, or drop the new sentinel and return `fmt.Errorf("void %s from %s: %w", inv.ID, inv.Status, ErrInvalidState)`, as `Finalize` does. The second option is simpler, since the status check already distinguishes the states.

**2. The new service is not registered in the worker** — `internal/worker/registration.go`
AGENTS.md says a new service is constructed in both `cmd/server/main.go` and `internal/worker/registration.go`. Only `main.go` was touched. `worker.Services` needs a `Voids service.VoidService` field and a `NewVoidService(...)` call in `Register`.

**3. Validation is duplicated in the handler** — `internal/api/void_handler.go:27`
Validation belongs in the service, and `Void()` already calls `req.Validate()`. The handler's call is redundant, and it also bypasses the shared error path (see 4). Remove it so the service is the single place, and let `writeError` handle the result. If the validation errors should map to 400, add a sentinel such as `ErrValidation` and map it in `writeError`. As written, a service-level validation failure (for example from a worker) would surface as a 500 via the HTTP path.

**4. Error is logged twice, and the layering is inconsistent** — `internal/service/void.go:116`
The service does `log.Printf(...)` and then returns the error. AGENTS.md says to log once, in the HTTP handler (`writeError` already does). Drop the `log.Printf` in the service. The "would notify customer" log is similarly a placeholder (see 7).

## Should fix

**5. Redundant defensive code that diverges from the repo patterns** — `internal/service/void.go`
- `if s.repo == nil { ... }`: constructors guarantee the dependency, and `Finalize` has no such check. Remove it.
- `if inv == nil { return nil, domain.ErrNotFound }`: the repo contract is "`Get` returns `ErrNotFound`" (`domain/invoice.go:37`), so a nil invoice with a nil error is not possible.
- The manual `TenantID`/`EnvironmentID` comparison after `Get`: the repo already scopes reads and writes by ctx (`inScope`), and AGENTS.md puts scoping in the repository. This check is a second, divergent copy of that rule. Remove it.
- `if len(inv.Lines) > 0 { for ... }`: the guard is a no-op. Just range.
- `getInvoice` is a one-line passthrough wrapper over `s.repo.Get`. Inline it.

**6. Unneeded abstractions** — `internal/service/void.go`
`VoidReasonFormatter`, `defaultVoidReasonFormatter` and the `formatter` field are an exported interface with one implementation that only does `TrimSpace`, and nothing can inject another one. Inline `strings.TrimSpace(req.Reason)`. Likewise `VoidOptions{NotifyCustomer}` is only used to emit a log line. Drop it unless a notifier is actually part of this PR. That also simplifies the constructor to `NewVoidService(repo, tx)`, matching `NewInvoiceService`.

**7. `RefundCents` is computed but nothing is refunded** — `internal/service/void.go`
`RefundCents` is the sum of the line amounts, which duplicates `TotalCents` already set at finalize. It is not clear what it means: nothing is refunded and no payment state is consulted. Either use `inv.TotalCents` or remove the field until refunds are in scope. If it stays, the name implies money movement that does not occur.

**8. Unrelated change in the memory repo** — `internal/repository/memory/invoice.go`
The `sort.Slice` in `List` has nothing to do with voiding. Move it to a separate PR, or explain why it is needed here. If it is for deterministic tests, say so.

## Nits / tests

- **No tests were added.** `fakeInvoiceService` has a counterpart pattern in `invoice_handler_test.go`. Please add a handler test with a fake `VoidService` (404, 409 already-voided, 400 bad body) and a service test covering the draft, finalized and already-void transitions, and the cross-tenant case.
- `void_handler.go`: `json.NewEncoder(w).Encode(res)` ignores the error. This matches the existing handlers, so it is fine.
- `Void` handler decodes the body with no size limit. Consider `http.MaxBytesReader`, given the 500-char reason.
- `len(r.Reason) > 500` counts bytes, not characters, but the message says "characters". Use `utf8.RuneCountInString`.
- The `// void the invoice` comment restates the code.

## Verdict
Request changes. The main points are the 500 on double-void (1), the missing worker registration (2), and the validation and logging layering (3, 4). Most of the rest is trimming code the repo's contracts already cover.

## Files read
- `AGENTS.md` (provided in context)
- `cmd/server/main.go` (via diff)
- `internal/api/void_handler.go` (via diff)
- `internal/repository/memory/invoice.go` (diff, then full)
- `internal/service/void.go` (via diff)
- `internal/worker/registration.go`
- `internal/service/invoice.go`
- `internal/api/invoice_handler.go`
- `internal/api/invoice_handler_test.go`
- `internal/domain/invoice.go` (only grep lines for `ErrNotFound`, `StatusVoid`, `VoidedAt`, `VoidReason`; not opened in full)
