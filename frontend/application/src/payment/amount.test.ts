import { describe, expect, it } from "vitest";
import { formatRub } from "./amount";
import { parseAmount } from "./paymentContext";

describe("formatRub", () => {
  it.each([
    ["1500000", 1500000],
    ["1500000,5", 1500000.5],
    ["12 500.25", 12500.25],
    ["700", 700],
  ])("formats %s in rubles and keeps the value parseable", (raw, amount) => {
    expect(parseAmount(formatRub(raw))).toBe(amount);
  });

  it("groups thousands and shows kopecks only when present", () => {
    expect(formatRub("1500000").replace(/\s/g, " ")).toBe("1 500 000");
    expect(formatRub("1500000,5").replace(/\s/g, " ")).toBe("1 500 000,50");
  });

  it("leaves invalid input untouched", () => {
    expect(formatRub("1500,")).toBe("1500,");
    expect(formatRub("")).toBe("");
  });
});
