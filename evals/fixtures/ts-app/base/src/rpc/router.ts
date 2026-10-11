import { createBillingService } from "../billing/service";
import { createInvoiceStore, type Database } from "../billing/store";
import { getInvoiceProcedure } from "./procedures/get-invoice";

export function createRouter({ db }: { db: Database }) {
  const invoices = createInvoiceStore({ db });
  const billing = createBillingService({ invoices });
  return {
    getInvoice: getInvoiceProcedure({ billing }),
  };
}
