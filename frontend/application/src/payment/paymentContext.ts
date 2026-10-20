import type { PaymentContext } from "@alpha-impact/plugin";

export interface PaymentForm {
  beneficiaryId: string;
  amount: string;
  purpose: string;
}

const CURRENCY = "RUB";

function parseAmount(raw: string): number | null {
  const normalized = raw.replace(/\s/g, "").replace(",", ".");
  if (normalized === "") {
    return null;
  }
  const amount = Number(normalized);
  return Number.isFinite(amount) && amount > 0 ? amount : null;
}

export function toPaymentContext(form: PaymentForm): PaymentContext | null {
  const amount = parseAmount(form.amount);
  if (form.beneficiaryId === "" || amount === null) {
    return null;
  }
  return { type: "payment", amount, beneficiary_id: form.beneficiaryId, currency: CURRENCY };
}
