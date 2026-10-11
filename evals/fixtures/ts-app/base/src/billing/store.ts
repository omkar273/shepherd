export interface Invoice {
  id: string;
  tenantId: string;
  customerId: string;
  status: "draft" | "open" | "paid";
  totalCents: number;
  creditAppliedCents: number;
}

export interface Customer {
  id: string;
  tenantId: string;
  creditBalanceCents: number | null;
}

export interface Database {
  query<T>(sql: string, params: ReadonlyArray<string | number>): Promise<T[]>;
}

export interface InvoiceStore {
  get(tenantId: string, id: string): Promise<Invoice | undefined>;
  save(invoice: Invoice): Promise<void>;
}

export function createInvoiceStore({ db }: { db: Database }): InvoiceStore {
  return {
    async get(tenantId, id) {
      const rows = await db.query<Invoice>(
        "select * from invoices where tenant_id = $1 and id = $2",
        [tenantId, id],
      );
      return rows[0];
    },
    async save(invoice) {
      await db.query(
        "update invoices set status = $1, credit_applied_cents = $2 where tenant_id = $3 and id = $4",
        [invoice.status, invoice.creditAppliedCents, invoice.tenantId, invoice.id],
      );
    },
  };
}

export interface CustomerStore {
  get(tenantId: string, id: string): Promise<Customer | undefined>;
  setCreditBalance(tenantId: string, id: string, cents: number): Promise<void>;
}

export function createCustomerStore({ db }: { db: Database }): CustomerStore {
  return {
    async get(tenantId, id) {
      const rows = await db.query<Customer>(
        "select * from customers where tenant_id = $1 and id = $2",
        [tenantId, id],
      );
      return rows[0];
    },
    async setCreditBalance(tenantId, id, cents) {
      await db.query(
        "update customers set credit_balance_cents = $1 where tenant_id = $2 and id = $3",
        [cents, tenantId, id],
      );
    },
  };
}
