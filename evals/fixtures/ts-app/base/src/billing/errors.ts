export type BillingErrorCode = "NOT_FOUND" | "ALREADY_PAID";

export class BillingError extends Error {
  readonly code: BillingErrorCode;

  constructor(code: BillingErrorCode, message: string) {
    super(message);
    this.code = code;
  }
}
