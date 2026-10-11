interface InvoiceLinkProps {
  invoiceId: string;
}

export function InvoiceLink({ invoiceId }: InvoiceLinkProps) {
  return <a href={`/invoices/${invoiceId}`}>View invoice</a>;
}
