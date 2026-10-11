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

