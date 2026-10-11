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

