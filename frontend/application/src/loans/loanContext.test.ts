import { describe, expect, it } from "vitest";
import type { Loan } from "../data/loans";
import { loanContextOf } from "./loanContext";

const LINE: Loan = {
  id: "loan-line",
  product: "Кредитная линия",
  kind: "loan",
  rateType: "floating",
  amount: 120_000_000,
  rate: "ключевая + 2,5%",
  maturity: "2027-06-30",
};

const LEASING: Loan = { ...LINE, id: "loan-leasing", product: "Лизинг", kind: "leasing", rateType: "fixed" };

describe("loanContextOf", () => {
  it("asks about a tranche of the credit line at its floating rate", () => {
    expect(loanContextOf(LINE, 50_000_000)).toEqual({
      type: "loan",
      product: "loan",
      amount: 50_000_000,
      rate_type: "floating",
    });
  });

  it("asks about leasing at its fixed rate", () => {
    expect(loanContextOf(LEASING, 10_000_000)).toEqual({
      type: "loan",
      product: "leasing",
      amount: 10_000_000,
      rate_type: "fixed",
    });
  });

  it.each([
    ["no product", undefined, 1000],
    ["no amount", LINE, null],
  ] as const)("has no context with %s", (_case, loan, amount) => {
    expect(loanContextOf(loan, amount)).toBeNull();
  });
});
