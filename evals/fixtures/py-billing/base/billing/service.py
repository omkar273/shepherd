from billing.errors import InvalidRequest, InvalidState, NotFound
from billing.models import Context, Invoice, Status
from billing.repo import InvoiceRepo

MAX_REASON = 500


class InvoiceService:
    def __init__(self, repo: InvoiceRepo):
        self.repo = repo

    def get(self, ctx: Context, invoice_id: str) -> Invoice:
        invoice = self.repo.get(invoice_id)
        if invoice.tenant_id != ctx.tenant_id:
            raise NotFound(invoice_id)
        return invoice

    def pay(self, ctx: Context, invoice_id: str) -> Invoice:
        with self.repo.lock(invoice_id):
            invoice = self.get(ctx, invoice_id)
            if invoice.status != Status.FINALIZED:
                raise InvalidState(f"cannot pay a {invoice.status.value} invoice")
            invoice.status = Status.PAID
            invoice.paid_cents = invoice.total_cents
            self.repo.save(invoice)
            return invoice

    def void(self, ctx: Context, invoice_id: str, reason: str) -> Invoice:
        if not reason.strip() or len(reason) > MAX_REASON:
            raise InvalidRequest(f"reason must be 1 to {MAX_REASON} characters")
        with self.repo.lock(invoice_id):
            invoice = self.repo.get(invoice_id)
            if invoice.tenant_id != ctx.tenant_id:
                raise NotFound(invoice_id)
            if invoice.status != Status.FINALIZED:
                raise InvalidState(f"cannot void a {invoice.status.value} invoice")
            invoice.status = Status.VOID
            invoice.void_reason = reason.strip()
            self.repo.save(invoice)
            return invoice
