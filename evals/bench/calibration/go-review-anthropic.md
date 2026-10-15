## Draft review: `feat/void-invoices` → `main`

`go build ./... && go vet ./...` passes on the branch. Findings below are ordered by severity.

### 1. `ErrAlreadyVoided` returns 500 instead of 409 (bug)
`internal/service/void.go:15`, `internal/api/invoice_handler.go` (`writeError`)

`ErrAlreadyVoided` is a new sentinel, but `writeError` only maps `domain.ErrNotFound` and `service.ErrInvalidState`. Voiding an already-voided invoice therefore falls through to `default` and returns `500 internal error`. That is a normal client-caused conflict.

Suggested fix: either add a `case errors.Is(err, service.ErrAlreadyVoided)` → `StatusConflict` to `writeError`, or wrap `ErrInvalidState` for this case. The second option keeps the existing handler mapping.

### 2. Void service is not registered in the worker (AGENTS.md violation)
`internal/worker/registration.go`

AGENTS.md says: "A new service is constructed in `cmd/server/main.go` and in `internal/worker/registration.go`." The PR adds `NewVoidService` only in `main.go`. The `Services` struct and `Register` in the worker need a `Voids service.VoidService` field and construction.

### 3. Validation is duplicated in the handler (AGENTS.md violation)
`internal/api/void_handler.go:27-31`

AGENTS.md says: "Validation lives in the service." The handler calls `req.Validate()`, and `voidService.Void` calls it again. Remove the handler call.

This also changes behavior: validation errors from the service currently come back as 500 through `writeError`. The service should return a typed validation error that the handler maps to 400. `FinalizeRequest` has the same gap today, so this could be a small follow-up, but it should not be solved by validating in the handler.

### 4. Logging in the service layer (AGENTS.md violation)
`internal/service/void.go`, the `log.Printf` calls on Update failure and on `NotifyCustomer`

AGENTS.md says: "Log once, in the HTTP handler." The handler's `writeError` already logs, so a failed update is logged twice. Drop the service-level logging. The Update error should be returned as-is, per "intermediate layers `return err`".

The `NotifyCustomer` branch only logs "would notify". It is a placeholder that does nothing, so remove it, or implement it behind a real dependency.

### 5. Redundant or dead code in `Void`
`internal/service/void.go`

- The `s.repo == nil` check can't happen, because the constructor is the only way to build the service.
- The `inv == nil` check is dead, because the repo contract returns `ErrNotFound`.
- The explicit tenant/environment comparison duplicates the repo scoping, which the repo already enforces on `Get` and `Update`. Please rely on the repo.
- `getInvoice` is a pass-through wrapper.
- The `len(inv.Lines) > 0` guard around the loop is unnecessary.
- `VoidReasonFormatter` and `defaultVoidReasonFormatter` are an interface with one trivial implementation, injectable by nobody.

None of these is wrong on its own, but together they add about 40 lines that make the service harder to review.

### 6. `RefundCents` is computed but nothing is refunded
`internal/service/void.go`

The result reports a "refund" that is just the sum of line amounts, and no refund is issued. It also ignores `inv.TotalCents`, and may differ from it for a finalized invoice. Please confirm the intent. If this is only informational, name it accordingly or use `inv.TotalCents`.

### 7. Unrelated change
`internal/repository/memory/invoice.go`

The `sort.Slice` added to `List` is unrelated to voiding. Split it into its own PR, or explain it in the description.

### 8. No tests
The PR adds a handler and a service with state transitions (void, already voided, wrong state, cross-tenant) and no tests. At minimum, add handler tests using a fake `VoidService`, as `invoice_handler_test.go` does, covering the 409 case from item 1.

### Files read
- `AGENTS.md` (provided in context)
- `cmd/server/main.go` (via diff)
- `internal/api/void_handler.go`
- `internal/api/invoice_handler.go`
- `internal/api/invoice_handler_test.go`
- `internal/service/void.go`
- `internal/service/invoice.go`
- `internal/repository/memory/invoice.go`
- `internal/domain/invoice.go`
- `internal/worker/registration.go`

Not opened: `internal/types/context.go`, `go.mod`.

Note: to read the branch I briefly ran `git checkout feat/void-invoices` and then `git checkout main`. The repo is back on `main` with no changes.
