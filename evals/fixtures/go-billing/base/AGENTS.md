# billing

- Services: an exported interface plus a private implementation in
  `internal/service`; constructors return the interface. Handler tests use
  fakes of these interfaces.
- Validation lives in the service. Workers and other services call services
  directly, so the service is the one place every entry point passes through.
- Every repository read and write is scoped by tenant and environment from ctx.
- Errors: intermediate layers `return err`. Add context only where the error
  originates. Log once, in the HTTP handler.
- A new service is constructed in `cmd/server/main.go` and in
  `internal/worker/registration.go`.
- Check: `go build ./... && go vet ./...`.
