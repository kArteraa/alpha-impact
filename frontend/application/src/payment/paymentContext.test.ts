import { describe, expect, it } from "vitest";
import { toPaymentContext } from "./paymentContext";

describe("toPaymentContext", () => {
  it("builds a payment context from a filled form", () => {
    expect(
      toPaymentContext({ beneficiaryId: "U_96105", amount: "1500000", purpose: "Оплата перевозки" }),
    ).toEqual({ type: "payment", amount: 1500000, beneficiary_id: "U_96105" });
  });

  it("accepts a decimal comma in the amount", () => {
    expect(toPaymentContext({ beneficiaryId: "U_22524", amount: "12 500,50", purpose: "" })?.amount).toBe(
      12500.5,
    );
  });

  it.each([
    ["no beneficiary", "", "1000"],
    ["empty amount", "U_22524", ""],
    ["zero amount", "U_22524", "0"],
    ["negative amount", "U_22524", "-5"],
    ["not a number", "U_22524", "abc"],
    ["hex literal", "U_22524", "0x10"],
    ["exponent", "U_22524", "1e6"],
    ["comma as thousands separator", "U_22524", "1,500"],
    ["fraction of a kopeck", "U_22524", "0.001"],
    ["more digits than a number keeps", "U_22524", "1234567890123456"],
  ])("returns null for %s", (_case, beneficiaryId, amount) => {
    expect(toPaymentContext({ beneficiaryId, amount, purpose: "" })).toBeNull();
  });
});
