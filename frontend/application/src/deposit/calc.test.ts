import { describe, expect, it } from "vitest";
import { DEPOSIT_TERMS, depositIncome } from "./calc";

describe("depositIncome", () => {
  it("accrues simple interest for the chosen term", () => {
    expect(depositIncome(1_000_000, 6, 16)).toBe(80_000);
    expect(depositIncome(2_500_000, 3, 14.5)).toBe(90_625);
  });

  it("rounds to kopecks", () => {
    expect(depositIncome(333_333, 12, 13.8)).toBe(45_999.95);
  });

  it("offers three, six and twelve months", () => {
    expect(DEPOSIT_TERMS).toEqual([3, 6, 12]);
  });
});
