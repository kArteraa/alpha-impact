import { parseAmount } from "./paymentContext";

const KOPECK_DIGITS = 2;

export function formatRub(raw: string): string {
  const amount = parseAmount(raw);
  if (amount === null) {
    return raw;
  }
  const digits = Number.isInteger(amount) ? 0 : KOPECK_DIGITS;
  return amount.toLocaleString("ru-RU", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
