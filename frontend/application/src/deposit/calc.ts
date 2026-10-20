export const DEPOSIT_TERMS = [3, 6, 12] as const;

export type DepositTerm = (typeof DEPOSIT_TERMS)[number];

const MONTHS_IN_YEAR = 12;
const PERCENT = 100;
const KOPECKS = 100;

export function depositIncome(amount: number, months: number, ratePercent: number): number {
  const income = (amount * ratePercent * months) / PERCENT / MONTHS_IN_YEAR;
  return Math.round(income * KOPECKS) / KOPECKS;
}
