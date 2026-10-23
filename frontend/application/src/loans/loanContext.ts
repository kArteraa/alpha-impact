import type { LoanContext } from "@alpha-impact/plugin";
import type { Loan } from "../data/loans";

export function loanContextOf(loan: Loan | undefined, amount: number | null): LoanContext | null {
  if (loan === undefined || amount === null) {
    return null;
  }
  return { type: "loan", product: loan.kind, amount, rate_type: loan.rateType };
}
