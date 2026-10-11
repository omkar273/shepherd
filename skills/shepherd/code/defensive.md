# Defensive checks

A check stays when it can fire: at a trust boundary, or in a case you can name.
Removing a check takes the same evidence as adding one.

## Trust boundaries

Data from something the code doesn't control:

- HTTP bodies, params, headers, query strings; CLI arguments.
- Env vars and config files.
- Webhooks and other inbound events; queue, job, and workflow payloads.
- Third-party API responses.
- Deserialized JSON columns and blobs; DB rows written by other systems or by
  older versions of this code.
- Uploaded files.

Not boundaries: in-repo calls whose callers you can grep, your own
constructor's result, data validated earlier on the same path, and anything
the type system guarantees.

## Never cut, even when another layer already does it

- Authentication, authorization, and ownership checks
  (`invoice.customerId !== ctx.customerId`).
- Tenant, environment, and org scoping: in queries, and re-checks in services.
  A second scoping check is defense in depth, not duplication.
- Money and quantity invariants (balance covers the amount, amount within what
  is due), state-machine guards (already paid, already voided), idempotency
  guards, uniqueness and integrity constraints.
- Transaction rollback, `defer` and `finally` cleanup, locks, optimistic
  version checks.
- Timeouts and retries around network I/O; error translation that callers rely
  on.
- Guards that stop a job, deploy, or pipeline from silently succeeding while
  doing nothing (a missing secret, an empty input set).
- Any check a comment explains or a test asserts.

Code that is moved or merged keeps its checks.

## Removing a check

All four must hold, and you write down the invariant ("`repo` can't be nil:
`NewVoidService` always sets it"):

1. It is not at a trust boundary.
2. Every caller has been grepped, including tests and string or dynamic
   references, and each one guarantees the condition; or the type system does.
3. It is not on the never-cut list.
4. Output for valid inputs is unchanged.

## Tiers

| Tier | Examples | Write mode | Review |
|---|---|---|---|
| HIGH | Empty catch. Catch that only rethrows. Log-and-return when a caller already logs. A nil or undefined guard on a value a type or constructor guarantees. Validation repeated on the same path (keep the copy every entry point passes through). | Cut | SHOULD |
| MEDIUM | Swallow-and-default (`?? 0`, `return nil` on error) on data that can really be missing. Log-only catch. Catch around I/O with no comment. Exported function whose callers you can't all see. A cast whose fix ripples outward. | Leave it; report it | ASK, as a question |
| LOW | Everything on the never-cut list | Keep | Say nothing |

## After removing

Run the repo's checks. A test that newly fails means the check was doing work:
restore it and report it. Never edit the test to make it pass. If a contract
now lies (a nullable return type, a doc line), flag it.

