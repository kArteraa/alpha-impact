import { describe, expect, it } from "vitest";
import { amountError, formatRub, parseAmount } from "./money";

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

  it("keeps the largest accepted amount valid after formatting", () => {
    const formatted = formatRub("9999999999999,99");
    expect(parseAmount(formatted)).toBe(9999999999999.99);
    expect(parseAmount("99999999999999")).toBeNull();
  });

  it("leaves invalid input untouched", () => {
    expect(formatRub("1500,")).toBe("1500,");
    expect(formatRub("")).toBe("");
  });
});

describe("amountError", () => {
  it("explains an amount it cannot accept", () => {
    expect(amountError("1500.555")).toBe("Сумма — положительное число, не больше двух знаков после запятой");
  });

  it.each(["", "  ", "1 500 000,50"])("has nothing to say about %j", (raw) => {
    expect(amountError(raw)).toBeNull();
  });
});
