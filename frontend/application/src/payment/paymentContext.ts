import type { PaymentContext } from "@alpha-impact/plugin";
import { parseAmount } from "../money";

export interface PaymentForm {
  beneficiaryId: string;
  amount: string;
  purpose: string;
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
