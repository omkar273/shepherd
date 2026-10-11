import { z } from "zod";
import { BillingError } from "../../billing/errors";
import type { BillingService } from "../../billing/service";
import type { RpcContext } from "../context";

const getInvoiceInput = z.object({ invoiceId: z.string().uuid() });

export function getInvoiceProcedure({ billing }: { billing: BillingService }) {
  return {
    input: getInvoiceInput,
    async handler(ctx: RpcContext, input: z.infer<typeof getInvoiceInput>) {
      const invoice = await billing.getInvoice(ctx.tenantId, input.invoiceId);
      if (invoice.customerId !== ctx.customerId) {
        throw new BillingError("NOT_FOUND", `invoice ${input.invoiceId} not found`);
      }
      return invoice;
    },
  };
}
