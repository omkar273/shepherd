---
paths:
  - "**/*.go"
  - "**/go.mod"
---

# Go

Run the tools first. A tool finding is the authority. Do not repeat a rule
here that a tool already reports.

1. `go build ./... && go vet ./...`.
2. The repo's lint target: a Makefile `lint` or `lint-ci`, or
   `golangci-lint run` if the repo has a `.golangci.*` file. golangci-lint
   runs staticcheck by default.
3. If the repo has staticcheck without golangci-lint, run it: `go tool
   staticcheck ./...` (a `tool` line in `go.mod`) or `staticcheck ./...`.
   Do not install a tool.

Impact: CRITICAL is a security, money, or data bug, or a feature that does
not work. HIGH is a bug in some cases, or a failure that nobody sees. MEDIUM
is code that adds nothing. Fix or flag the CRITICAL items first.

## Keep

- **CRITICAL.** Tenant, owner, and state checks in a service, also when the
  repo or the handler checks too. Workers and other services call the
  service directly.
  ```go
  // bad: "store.Get already scopes by org", so the re-check goes
  // good: keep both
  if o.OrgID != authz.OrgID(ctx) { return nil, ErrNotFound }
  if o.Status != StatusOpen { return nil, ErrNotOpen }
  ```
- **CRITICAL.** `defer tx.Rollback()` right after `Begin`. After a commit,
  `Rollback` is a no-op. Without it, an early return leaves the
  transaction and its locks open.
  ```go
  tx, err := db.BeginTx(ctx, nil)
  if err != nil { return err }
  defer tx.Rollback() // keep, also with tx.Commit() below
  ```
- **HIGH.** `errors.Is` and `errors.As` for a wrapped error. `==` fails after
  `fmt.Errorf("...: %w", err)`.
  ```go
  if err == sql.ErrNoRows { ... }          // bad
  if errors.Is(err, sql.ErrNoRows) { ... } // good
  ```
- **HIGH.** `defer rows.Close()` and `defer resp.Body.Close()` after the
  error check. Without them, the connection pool leaks.
  ```go
  resp, err := client.Do(req)
  if err != nil { return err }
  defer resp.Body.Close()
  ```
- **HIGH.** `ctx` as the first parameter, passed down to each call. A
  goroutine has an owner that waits for it and a `ctx` that stops it.
  ```go
  go s.sync(context.Background()) // bad: no cancel, nobody waits
  g.Go(func() error { return s.sync(ctx) }) // good: errgroup
  ```
- **HIGH.** nil checks on pointers from nullable columns, optional JSON
  fields, and map lookups. A nil pointer there panics.
- **MEDIUM.** A bare `if err != nil { return nil, err }` in intermediate
  layers. Add context once, where the error occurs, with the repo's error
  package or `fmt.Errorf("...: %w", err)`.
- **MEDIUM.** `var _ Iface = (*T)(nil)` compile-time assertions, and nil-safe
  getters when the repo's rules require them.

## Cut

- **MEDIUM.** A guard that Go already gives: `len(s) > 0` before `range s`, a
  nil check before a read from a nil map, a nil check before `len(x)`.
  ```go
  if len(o.Items) > 0 { for _, it := range o.Items { ... } } // bad
  for _, it := range o.Items { ... }                         // good
  ```
- **MEDIUM.** A nil check on a value whose constructor or repository
  contract never returns nil together with a nil error.
  ```go
  o, err := s.store.Get(ctx, id)
  if err != nil { return nil, err }
  if o == nil { return nil, ErrNotFound } // bad: Get never returns nil, nil
  ```
- **MEDIUM.** Validation of the same request in the handler and in the
  service. Keep the service copy, because workers and other services call it
  too. If the handler copy exists only for a 400, map the service error to
  400.
- **MEDIUM.** Code that logs an error and also returns it. Log once, at the
  boundary that owns the failure.
- **MEDIUM.** Code that wraps the same error again at each layer, and a `%w`
  that adds no context.
- **MEDIUM.** Mutexes or channels around state that no other goroutine
  touches.
- **MEDIUM.** A new interface outside the repo's convention with one
  implementation and no fake. Many repos declare an interface for each
  service next to its private implementation. In those repos, the interface
  is the convention. Before you flag one, grep `_test.go` files, `testutil/`,
  and `fake`, `stub`, or `mock` types. A hit means the interface stays.

## Boundaries

Decode and validate at these points. After that, pass the typed value and do
not check it again.

- Request bind and decode.
- Env and config, which the program parses once at startup.
- JSON or `[]byte` from the DB.
- External client responses.
- Queue, workflow, and activity payloads.
- Webhooks.

## Wiring

- **CRITICAL.** Every place where the repo constructs services. That is the
  DI container (fx, wire, or a hand-written `main.go`), and each worker, job,
  or workflow registration that builds its own instances. A service that only
  `main.go` builds does not run in the worker.
- **CRITICAL.** Routes, and the error-to-HTTP-status mapping for each new
  error value. An unmapped error becomes a 500.
  ```go
  // bad: ErrAlreadyShipped falls through to 500
  // good
  case errors.Is(err, orders.ErrAlreadyShipped):
      status = http.StatusConflict
  ```
- **HIGH.** Generated code (ent, sqlc, mocks, swagger, SDKs): run the repo's
  generate target. Never edit the output by hand.
- **MEDIUM.** `//go:build` tags on new files that need them.
