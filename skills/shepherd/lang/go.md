# Go

Run `go build ./... && go vet ./...`. Also run the repo's lint target: a
Makefile `lint` or `lint-ci`, or golangci-lint if the repo configures it.

## Idiomatic: keep

- `if err != nil { return err }` in intermediate layers. Add context once,
  where the error occurs, with the repo's error package or
  `fmt.Errorf("...: %w", err)`.
- `defer rows.Close()`, `defer tx.Rollback()` (after a commit,
  `tx.Rollback()` is a no-op).
- `ctx` as the first parameter, and `ctx.Err()` checks in long loops.
- nil checks on pointers from nullable columns, optional JSON fields, or map
  lookups.
- `var _ Iface = (*T)(nil)` compile-time assertions.
- nil-safe getters or builders when the repo's rules require them.

## Interfaces

Follow the repo's convention for new services. Many repos declare an
interface for each service next to its private implementation, and return
the interface from the constructor. In those repos, this interface is the
convention, not over-engineering.

Before you flag any interface, grep `_test.go` files, `testutil/`, and
`fake`, `stub`, or `mock` types for implementations. A hit means that the
interface is load-bearing. Flag only a new interface that is outside the
convention, has one implementation, and has no fake.

## Noise: cut

- `len(s) > 0` before `range s`, a check before a read from a nil map, and a
  nil check before `len(x)`.
- A nil check on a value whose constructor or repository contract never
  returns nil together with a nil error.
- Code that re-wraps or re-marks the same error at every layer, and a `%w`
  that adds no context.
- Code that logs an error and also returns it. Log once, at the boundary that
  owns the failure.
- Mutexes or channels around state that no other goroutine touches.
- Validation of the same request in the handler and in the service. Keep the
  copy that every entry point passes through. Usually this copy is in the
  service, because workers and other services call it too. Delete the other
  copy. If the handler copy exists only to produce a 400, map the service's
  validation error to 400 instead.

## Boundaries

- Request bind and decode.
- Env and config, which the program parses once at startup.
- JSON or `[]byte` from the DB.
- External client responses.
- Queue, workflow, and activity payloads.
- Webhooks.

## Wiring

- Every place where the repo constructs services:
  - The DI container (fx, wire, or a hand-written `main.go`).
  - Any worker, job, or workflow registration that builds its own instances.
- Routes, and the error-to-HTTP-status mapping for every new error value.
- Generated code (ent, sqlc, mocks, swagger, SDKs): run the repo's generate
  target. Never hand-edit the output.
- `//go:build` tags.
