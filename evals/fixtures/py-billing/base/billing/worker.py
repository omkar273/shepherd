from billing.models import Context
from billing.service import InvoiceService


def process_job(service: InvoiceService, job: dict) -> None:
    ctx = Context(tenant_id=job["tenant_id"], user_id="worker")
    if job["kind"] == "void":
        service.void(ctx, job["invoice_id"], job["reason"])
    elif job["kind"] == "pay":
        service.pay(ctx, job["invoice_id"])
    else:
        raise ValueError(f"unknown job kind {job['kind']}")
