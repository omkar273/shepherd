import unittest

from billing.http import dispatch
from billing.models import Context, Invoice, Status
from billing.money import fmt_cents
from billing.repo import InvoiceRepo
from billing.service import InvoiceService
from billing.worker import process_job

ACME = Context(tenant_id="acme", user_id="u1")
GLOBEX = Context(tenant_id="globex", user_id="u2")


def service_with(*invoices):
    repo = InvoiceRepo()
    for invoice in invoices:
        repo.add(invoice)
    return InvoiceService(repo)


def finalized(invoice_id="inv1", tenant_id="acme"):
    return Invoice(id=invoice_id, tenant_id=tenant_id, customer_id="c1", status=Status.FINALIZED,
                   total_cents=1250)


class MoneyTests(unittest.TestCase):
    def test_fmt_cents(self):
        self.assertEqual(fmt_cents(1250), "12.50")
        self.assertEqual(fmt_cents(5), "0.05")


class HttpTests(unittest.TestCase):
    def test_get_other_tenant_is_not_found(self):
        status, _ = dispatch(service_with(finalized()), GLOBEX, "GET", "invoice", "inv1", {})
        self.assertEqual(status, 404)

    def test_void(self):
        status, body = dispatch(service_with(finalized()), ACME, "POST", "invoice/void", "inv1",
                                {"reason": "duplicate"})
        self.assertEqual((status, body["status"], body["previous"]), (200, "void", "finalized"))

    def test_void_other_tenant_is_not_found(self):
        status, _ = dispatch(service_with(finalized()), GLOBEX, "POST", "invoice/void", "inv1",
                             {"reason": "duplicate"})
        self.assertEqual(status, 404)

    def test_pay_twice_conflicts(self):
        service = service_with(finalized())
        dispatch(service, ACME, "POST", "invoice/pay", "inv1", {})
        status, _ = dispatch(service, ACME, "POST", "invoice/pay", "inv1", {})
        self.assertEqual(status, 409)


class WorkerTests(unittest.TestCase):
    def test_void_job(self):
        service = service_with(finalized())
        process_job(service, {"kind": "void", "tenant_id": "acme", "invoice_id": "inv1",
                              "reason": "dunning"})
        self.assertEqual(service.get(ACME, "inv1").status, Status.VOID)


if __name__ == "__main__":
    unittest.main()
