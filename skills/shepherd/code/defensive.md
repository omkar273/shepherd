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

