# Go

Run `go build ./... && go vet ./...` plus the repo's lint target (a Makefile
`lint` or `lint-ci`, golangci-lint if configured).

## Idiomatic: keep

- `if err != nil { return err }` in intermediate layers. Context is added once,
  where the error originates, with the repo's error package or
  `fmt.Errorf("...: %w", err)`.
- `defer rows.Close()`, `defer tx.Rollback()` (a no-op after commit).
- `ctx` as the first parameter; `ctx.Err()` checks in long loops.
- nil checks on pointers from nullable columns, optional JSON fields, or map
  lookups.
- `var _ Iface = (*T)(nil)` compile-time assertions.
- nil-safe getters or builders when the repo's rules require them.

## Interfaces

Follow the repo's convention for new services. Many repos declare an
interface per service next to its private implementation and return it from
the constructor; there, that is the pattern, not over-engineering. Before
flagging any interface, grep `_test.go` files, `testutil/`, and `fake`, `stub`,
or `mock` types for implementations. A hit means the interface is
load-bearing. Flag only a new interface outside the convention with one
implementation and no fake.

## Noise: cut

- `len(s) > 0` before `range s`; a guard before reading a nil map; a nil check
  before `len(x)`.
- A nil check on a value whose constructor or repository contract never
  returns nil alongside a nil error.
- Re-wrapping or re-marking the same error at every layer; `%w` that adds no
  context.
- Logging an error and also returning it. Log once, at the boundary that owns
  the failure.
- Mutexes or channels around state no other goroutine touches.
- The same request validated in the handler and in the service. Keep the copy
  every entry point passes through (usually the service, since workers and
  other services call it too) and delete the other. If the handler copy exists
  only to produce a 400, map the service's validation error to 400 instead.

