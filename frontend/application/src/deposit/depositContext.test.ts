import { describe, expect, it } from "vitest";
import { depositContextOf } from "./depositContext";

describe("depositContextOf", () => {
  it.each([
    [3, 90],
    [6, 180],
    [12, 360],
  ] as const)("asks about %i months as %i days of the whatif calculator", (term, days) => {
    expect(depositContextOf(50_000_000, term)).toEqual({ type: "deposit", amount: 50_000_000, term_days: days });
  });

  it("has no context without an amount", () => {
    expect(depositContextOf(null, 6)).toBeNull();
  });
});
