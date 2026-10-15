---
paths:
  - "**/*.py"
  - "**/*.pyi"
  - "**/pyproject.toml"
---

# Python

Run the tools first. A tool finding is the authority. Do not repeat a rule
here that a tool already reports.

1. The repo's test command, from its docs, Makefile, `tox.ini`, `noxfile.py`,
   or CI.
2. Each checker that the repo configures in `pyproject.toml`, `ruff.toml`,
   `setup.cfg`, `mypy.ini`, or `pyrightconfig.json`: ruff, mypy, pyright, or
   flake8. Run it through the repo's runner (`uv run`, `poetry run`, a
   Makefile target) if it has one.

Do not install a tool, and do not add a dependency. If the repo says
"standard library only", keep to it.

Impact: CRITICAL is a security, money, or data bug, or a feature that does
not work. HIGH is a bug in some cases, or a failure that nobody sees. MEDIUM
is code that adds nothing. Fix or flag the CRITICAL items first.

## Keep

- **CRITICAL.** Tenant, owner, state, and idempotency checks in a service,
  also when the handler checks too. Workers and scripts can call the service
  directly.
  ```python
  if order.org_id != ctx.org_id:          # keep
      raise NotFound(order_id)
  if request_id in order.request_ids:     # keep: a retry must not apply twice
      return order
  ```
- **CRITICAL.** `with` blocks for locks, transactions, and files, and
  `try`/`finally` cleanup. Do not unwrap them to make the code shorter.
  ```python
  with db.transaction():  # keep: both rows change, or neither does
      stock.reserve(sku, qty)
      orders.add(order)
  ```
- **CRITICAL.** Money in integer cents or `Decimal`, never `float`.
  ```python
  total = sum(line.price for line in lines)            # bad: 0.1 + 0.2 != 0.3
  total_cents = sum(line.price_cents for line in lines)  # good
  ```
- **HIGH.** `raise ... from err` when you translate an error, so that the
  cause stays in the traceback. Catch the narrowest error.
  ```python
  except Exception: raise NotFound(key)                  # bad
  except KeyError as err: raise NotFound(key) from err   # good
  ```
- **HIGH.** Time zones on datetimes. `datetime.utcnow()` returns a naive
  value. `.timestamp()` reads it as local time, and a compare with an aware
  value raises `TypeError`.
  ```python
  now = datetime.utcnow()              # bad
  now = datetime.now(timezone.utc)     # good
  ```
- **MEDIUM.** `is None` checks on values that can really be `None`:
  `dict.get`, nullable columns, and `Optional` fields.

## Cut

- **HIGH.** A mutable default argument. All calls share one list or dict.
  ```python
  def add(item, items=[]): ...          # bad
  def add(item, items=None): items = [] if items is None else items  # good
  ```
- **HIGH.** A broad `except` that swallows the error (`except Exception: pass`,
  a `return None` in the handler). The failure disappears. Catch the
  specific error, or let it go up.
  ```python
  except Exception: return None          # bad: nobody sees the failure
  except TimeoutError: retry_later(job)  # good: catch what you can handle
  ```
- **MEDIUM.** A `try` that only raises again.
  ```python
  try: self.store.save(order)
  except Exception: raise                # bad: delete the try
  ```
- **MEDIUM.** An `is None` check after a call that raises instead of
  returning `None`.
  ```python
  order = self.store.get(order_id)  # raises NotFound
  if order is None: ...             # bad: never true
  ```
- **MEDIUM.** An ABC or `Protocol` with one implementation and no fake. Grep
  `tests/` for fakes before you flag it.
- **MEDIUM.** A method that only forwards to one call, and a `@property` or
  getter that only returns an attribute.
- **MEDIUM.** A flag or keyword argument that no caller sets, and a branch
  that only logs "would do X".
- **MEDIUM.** Logging outside the module that owns it, and code that logs an
  error and also raises it. Log once, at the boundary.
- **MEDIUM.** `if items:` or `if len(items) > 0:` before a `for` loop over
  `items`.

## Boundaries

Parse at these points with the repo's tool (pydantic, attrs, marshmallow, or
a `parse_*` function). After that, pass the typed value and do not check it
again with `isinstance` or a range test.

- Request bodies, query params, and headers.
- Env and config, which the program parses once at startup.
- JSON from the DB, files, or caches.
- External API responses.
- Queue and task payloads, webhooks, and CLI arguments.

## Wiring

- **CRITICAL.** Route registration: the route table, `urls.py`,
  `include_router`, or a blueprint. A handler that no route lists is
  unreachable.
  ```python
  router = APIRouter(prefix="/orders")  # bad: no include_router, so no route
  app.include_router(orders.router)    # good
  ```
- **CRITICAL.** The error-to-status mapping for each new exception. An
  unmapped exception becomes a 500.
  ```python
  STATUS = {OrderNotFound: 404}                   # bad: OutOfStock is missing
  STATUS = {OrderNotFound: 404, OutOfStock: 409}  # good
  ```
- **HIGH.** Task and job registration (Celery, RQ, the repo's worker table),
  Django `INSTALLED_APPS`, and migrations for each model change.
  ```python
  def ship_order(order_id): ...                  # bad: the worker cannot find it
  @app.task
  def ship_order(order_id): ...                  # good
  ```
- **MEDIUM.** `__init__.py` exports and `__all__` if the repo routes imports
  through them, and `[project.scripts]` entry points.
