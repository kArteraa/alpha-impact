import type { DepositContext } from "@alpha-impact/plugin";
import type { DepositTerm } from "./calc";

const DAYS_IN_MONTH = 30;

export function depositContextOf(amount: number | null, term: DepositTerm): DepositContext | null {
  if (amount === null) {
    return null;
  }
  return { type: "deposit", amount, term_days: term * DAYS_IN_MONTH };
}
