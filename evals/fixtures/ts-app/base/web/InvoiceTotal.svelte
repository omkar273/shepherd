<script lang="ts">
  import type { Invoice } from "../src/billing/store";

  interface InvoiceTotalProps {
    invoice: Invoice;
  }

  let { invoice }: InvoiceTotalProps = $props();
</script>

<p>Total: {(invoice.totalCents / 100).toFixed(2)}</p>
