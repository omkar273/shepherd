# billing

- Standard library only. Python 3.11 or later.
- `billing/http.py` parses each request body once (`parse_*`). Services take
  the parsed values and do not check them again.
- HTTP handlers and the job worker (`billing/worker.py`) call
  `InvoiceService` directly. The admin tool and the dunning scheduler queue
  jobs for the worker.
- A handler is reachable only from `ROUTES` in `billing/http.py`.
- Every domain error has a status in `ERROR_STATUS` in `billing/http.py`.
- Log once, in `billing/http.py`.
- Check: `python3 -m unittest`.
