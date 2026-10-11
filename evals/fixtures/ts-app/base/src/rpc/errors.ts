import { BillingError, type BillingErrorCode } from "../billing/errors";

function httpStatus(code: BillingErrorCode): number {
  switch (code) {
    case "NOT_FOUND":
      return 404;
    case "ALREADY_PAID":
      return 409;
  }
}

export function toHttpError(error: Error): { status: number; message: string } {
  if (error instanceof BillingError) {
    return { status: httpStatus(error.code), message: error.message };
  }
  console.error(error);
  return { status: 500, message: "internal error" };
}
