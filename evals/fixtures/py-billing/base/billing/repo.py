import threading
from contextlib import contextmanager

from billing.errors import NotFound
from billing.models import Invoice


class InvoiceRepo:
    def __init__(self):
        self._invoices: dict[str, Invoice] = {}
        self._locks: dict[str, threading.Lock] = {}

    def add(self, invoice: Invoice) -> None:
        self._invoices[invoice.id] = invoice

    def get(self, invoice_id: str) -> Invoice:
        try:
            return self._invoices[invoice_id]
        except KeyError:
            raise NotFound(invoice_id) from None

    def save(self, invoice: Invoice) -> None:
        self._invoices[invoice.id] = invoice

    @contextmanager
    def lock(self, invoice_id: str):
        with self._locks.setdefault(invoice_id, threading.Lock()):
            yield
