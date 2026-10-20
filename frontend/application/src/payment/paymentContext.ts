import type { PaymentContext } from "@alpha-impact/plugin";

export interface PaymentForm {
  beneficiaryId: string;
  amount: string;
  purpose: string;
}

const AMOUNT_PATTERN = /^\d+([.,]\d{1,2})?$/;

export function parseAmount(raw: string): number | null {
  const compact = raw.replace(/\s/g, "");
  if (!AMOUNT_PATTERN.test(compact)) {
    return null;
  }
  const amount = Number(compact.replace(",", "."));
  return amount > 0 ? amount : null;
}

export function paymentContextOf(beneficiaryId: string, amount: number | null): PaymentContext | null {
  if (beneficiaryId === "" || amount === null) {
    return null;
  }
  return { type: "payment", amount, beneficiary_id: beneficiaryId };
}

export function toPaymentContext(form: PaymentForm): PaymentContext | null {
  return paymentContextOf(form.beneficiaryId, parseAmount(form.amount));
}
