# Draft review: `feat/void-invoices` → `main`

Overall the shape is right (interface + private impl, constructor returns interface, validation in the service, tenant/env scoped). A few things need fixing before merge. I haven't run `go build ./... && go vet ./...` on this branch.

## Blocking

**1. Worker registration is missing** (`internal/worker/registration.go`)
AGENTS.md requires a new service to be constructed in both `cmd/server/main.go` and `internal/worker/registration.go`. The PR only does `main.go`. Please add `Voids service.VoidService` to `worker.Services` and construct it in `Register`.

**2. `ErrAlreadyVoided` returns 500** (`internal/service/void.go`, `internal/api/invoice_handler.go:21`)
`writeError` only maps `ErrNotFound` and `ErrInvalidState`. `ErrAlreadyVoided` falls through to `500 internal error`. A double-void is a client error, so it should be a 409. Either:
- return `ErrInvalidState` wrapped (as Finalize does), or
- add a case in `writeError`.

The first is simpler. The second sentinel isn't needed.

**3. Missing `inv.Status == StatusVoid` handling vs. error context**
`ErrInvalidState` is returned bare, while Finalize wraps it with `fmt.Errorf("finalize %s from %s: %w", ...)`. Per AGENTS.md, context goes where the error originates, so wrap it here too (`void %s from %s: %w`).

**4. Logging outside the HTTP handler** (`void.go`, `Update` failure and `NotifyCustomer` branch)
AGENTS.md says to log once, in the HTTP handler. The `log.Printf` on Update failure double-logs, because `writeError` already logs. Remove it and just `return err`. The "would notify customer" log is a placeholder with no behavior; drop it (see 7).

**5. Validation duplicated in the handler** (`void_handler.go`)
`req.Validate()` is called in the handler and again in the service. Validation belongs only in the service. Remove it from the handler. As written, handler tests with a fake service would also skip the real validation path. Note that the service returns a plain `errors.New`, which `writeError` maps to 500. A validation failure should be a 400, so introduce a validation error type or sentinel (e.g. `ErrValidation`) and map it in `writeError`. That's what keeps this from being a 500 once the handler check is removed.

## Should fix

**6. Refund amount is a guess** (`void.go`)
`RefundCents` is the sum of line amounts, but nothing is refunded and no refund is recorded or persisted. Finalize already computes `TotalCents`. Use `inv.TotalCents`, or drop the field until refunds exist. It's also only meaningful if the invoice was paid. Please clarify intent.

**7. Unneeded abstractions / dead code**
- `VoidReasonFormatter` and `defaultVoidReasonFormatter` have a single trivial implementation and no way to inject another. Inline `strings.TrimSpace`.
- `VoidOptions.NotifyCustomer` only logs. Remove it until notifications exist, which also simplifies the constructor signature.
- `getInvoice` is a one-line passthrough to `repo.Get`; call `s.repo.Get` directly as Finalize does.
- `if s.repo == nil` is a constructor concern, not per-call. Remove.
- `if inv == nil` and the manual tenant/env check: the repo already scopes by ctx and returns `ErrNotFound`, so both are redundant. Per the repo-scoping rule the repo is the right place; the duplicate check in the service is noise.
- `if len(inv.Lines) > 0` wrapping the loop is redundant.

**8. Unrelated change** (`internal/repository/memory/invoice.go`)
The `sort.Slice` in `List` is unrelated to voiding. Split it into its own PR, or explain why it's needed here.

## Nits / questions

- `VoidRequest.Validate` checks `len(r.Reason) > 500` on bytes, not characters. Use `utf8.RuneCountInString` if the limit is meant as characters.
- `VoidRequest.InvoiceID` is tagged `json:"-"` and then set by the handler. That's fine, but `Void` in the handler should mention that in a comment or follow Finalize's inline struct literal.
- `json.NewEncoder(w).Encode(res)` returns `VoidResult` with no JSON tags, so the response uses Go field names (`Invoice`, `RefundCents`). Add tags if this is a public API.
- There are no tests: service tests (happy path, already void, wrong state, wrong tenant) and a handler test with a fake `VoidService` (see `invoice_handler_test.go`).
- Concurrency: two concurrent voids can both read `finalized` and both succeed, since there's no locking or conditional update. This is fine for the in-memory repo; flag it for a real DB.

## Files read
- `AGENTS.md` (provided in context)
- `cmd/server/main.go` (via diff)
- `internal/api/void_handler.go` (via diff)
- `internal/service/void.go` (via diff)
- `internal/repository/memory/invoice.go`
- `internal/service/invoice.go`
- `internal/worker/registration.go`
- `internal/api/invoice_handler.go` (grep output only, lines 21–46)
- `internal/domain/invoice.go` (grep output only, lines 16, 33, 34)

Note: I briefly ran `git checkout feat/void-invoices` to read the files and then switched back to `main`. The working tree is clean and nothing was modified. I did not open `invoice_handler_test.go` or `internal/types/context.go`.
