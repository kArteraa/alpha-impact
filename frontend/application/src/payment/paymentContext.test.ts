import { describe, expect, it } from "vitest";
import { toPaymentContext } from "./paymentContext";

describe("toPaymentContext", () => {
  it("builds a payment context from a filled form", () => {
    expect(
      toPaymentContext({ beneficiaryId: "cp_logistics_spb", amount: "1500000", purpose: "Оплата перевозки" }),
    ).toEqual({ type: "payment", amount: 1500000, beneficiary_id: "cp_logistics_spb", currency: "RUB" });
  });

  it("accepts a decimal comma in the amount", () => {
    expect(toPaymentContext({ beneficiaryId: "cp_stationery", amount: "12 500,50", purpose: "" })?.amount).toBe(
      12500.5,
    );
  });

  it.each([
    ["no beneficiary", "", "1000"],
    ["empty amount", "cp_stationery", ""],
    ["zero amount", "cp_stationery", "0"],
    ["negative amount", "cp_stationery", "-5"],
    ["not a number", "cp_stationery", "abc"],
  ])("returns null for %s", (_case, beneficiaryId, amount) => {
    expect(toPaymentContext({ beneficiaryId, amount, purpose: "" })).toBeNull();
  });
});
