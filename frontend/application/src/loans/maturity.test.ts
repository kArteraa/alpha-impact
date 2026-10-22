import { describe, expect, it } from "vitest";
import { daysUntil } from "./maturity";

const NOW = new Date("2026-10-22T09:30:00+03:00");

describe("daysUntil", () => {
  it.each([
    ["2026-12-31", 70],
    ["2026-10-23", 1],
    ["2026-10-22", 0],
    ["2026-10-01", -21],
  ])("counts calendar days to %s", (date, days) => {
    expect(daysUntil(date, NOW)).toBe(days);
  });
});
