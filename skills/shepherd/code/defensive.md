# Defensive checks

A check stays when it can fire: at a trust boundary, or in a case that you
can name. You need the same evidence to remove a check as to add one.

## Trust boundaries

Data from something that the code does not control is at a trust boundary:

- HTTP bodies, params, headers, and query strings.
- CLI arguments.
- Env vars and config files.
- Webhooks and other inbound events.
- Queue, job, and workflow payloads.
- Third-party API responses.
- Deserialized JSON columns and blobs.
- DB rows that other systems, or older versions of this code, wrote.
- Uploaded files.

These are not at a trust boundary:

- In-repo calls whose callers you can grep.
- The result of your own constructor.
- Data that the code validated earlier on the same path.
- Anything that the type system guarantees.

## Never cut, even when another layer already does it

- Authentication, authorization, and ownership checks
  (`invoice.customerId !== ctx.customerId`).
- Tenant, environment, and org scoping: in queries, and as re-checks in
  services. A second scoping check is defense in depth, not duplication.
- Money and quantity invariants (the balance covers the amount, the amount is
  within what is due).
- State-machine guards (already paid, already voided).
- Idempotency guards, and uniqueness and integrity constraints.
- Transaction rollback, `defer` and `finally` cleanup, locks, and optimistic
  version checks.
- Timeouts and retries around network I/O.
- Error translation that callers rely on.
- Guards against a job, deploy, or pipeline that silently succeeds but does
  nothing (a missing secret, an empty input set).
- Any check that a comment explains or that a test asserts.

When you move or merge code, keep its checks.

## Removing a check

To remove a check, write down the invariant ("`repo` can't be nil:
`NewVoidService` always sets it"). All four conditions below must also be
true:

1. It is not at a trust boundary.
2. You grepped every caller, including tests and string or dynamic
   references, and each caller guarantees the condition. Or the type system
   guarantees it.
3. It is not on the never-cut list.
4. The output for valid inputs does not change.

## Tiers

| Tier | Examples | Write mode | Review |
|---|---|---|---|
| HIGH | An empty catch. A catch that only rethrows. A log-and-return when a caller already logs. A nil or undefined guard on a value that a type or constructor guarantees. Validation repeated on the same path (keep the copy that every entry point passes through). | Cut | SHOULD |
| MEDIUM | A swallow-and-default (`?? 0`, `return nil` on error) on data that can really be missing. A log-only catch. A catch around I/O with no comment. An exported function whose callers you cannot all see. A cast whose fix spreads to other code. | Leave it. Report it. | ASK, as a question |
| LOW | Everything on the never-cut list | Keep | Say nothing |

## After removing

Run the repo's checks. If a test newly fails, the removed check did work.
Restore the check and report it. Never edit the test to make it pass. If a
contract is now false (a nullable return type, a doc line), flag it.

## Adding

Add a check only at a trust boundary, or for a case that you can name. Let
errors propagate to the layer that handles them. Never turn an error into a
silent default.
