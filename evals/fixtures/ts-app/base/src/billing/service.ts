import { BillingError } from "./errors";
import type { Invoice, InvoiceStore } from "./store";

export interface BillingService {
  getInvoice(tenantId: string, id: string): Promise<Invoice>;
}

export function createBillingService({ invoices }: { invoices: InvoiceStore }): BillingService {
  return {
    async getInvoice(tenantId, id) {
      const invoice = await invoices.get(tenantId, id);
      if (invoice === undefined) {
        throw new BillingError("NOT_FOUND", `invoice ${id} not found`);
      }
      return invoice;
    },
  };
}
