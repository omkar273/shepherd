import logging

from billing.errors import BillingError, InvalidRequest, InvalidState, NotFound
from billing.models import Context
from billing.money import fmt_cents
from billing.service import InvoiceService

log = logging.getLogger(__name__)

ERROR_STATUS = {
    NotFound: 404,
    InvalidState: 409,
    InvalidRequest: 400,
}


def parse_void(body: dict) -> str:
    reason = body.get("reason")
    if not isinstance(reason, str):
        raise InvalidRequest("reason must be a string")
    return reason


def render(invoice) -> dict:
    return {
        "id": invoice.id,
        "status": invoice.status.value,
        "total": fmt_cents(invoice.total_cents),
        "paid": fmt_cents(invoice.paid_cents),
    }


def handle_get(service: InvoiceService, ctx: Context, invoice_id: str, body: dict) -> dict:
    return render(service.get(ctx, invoice_id))


def handle_pay(service: InvoiceService, ctx: Context, invoice_id: str, body: dict) -> dict:
    return render(service.pay(ctx, invoice_id))


def handle_void(service: InvoiceService, ctx: Context, invoice_id: str, body: dict) -> dict:
    reason = parse_void(body)
    previous = service.get(ctx, invoice_id).status.value
    return {**render(service.void(ctx, invoice_id, reason)), "previous": previous}


ROUTES = {
    ("GET", "invoice"): handle_get,
    ("POST", "invoice/pay"): handle_pay,
    ("POST", "invoice/void"): handle_void,
}


def dispatch(service: InvoiceService, ctx: Context, method: str, route: str, invoice_id: str,
             body: dict) -> tuple[int, dict]:
    handler = ROUTES.get((method, route))
    if handler is None:
        return 404, {"error": "no route"}
    try:
        return 200, handler(service, ctx, invoice_id, body)
    except BillingError as exc:
        log.warning("%s %s failed: %s", method, route, exc)
        return ERROR_STATUS.get(type(exc), 500), {"error": str(exc)}
