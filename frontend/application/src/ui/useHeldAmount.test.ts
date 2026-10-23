import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useHeldAmount } from "./useHeldAmount";

function typed(first: string) {
  return renderHook(({ text }) => useHeldAmount(text), { initialProps: { text: first } });
}

describe("useHeldAmount", () => {
  it("reads the amount from the field", () => {
    expect(typed("1 500 000,50").result.current).toBe(1_500_000.5);
  });

  it("holds the last amount while the next one is being typed", () => {
    const { result, rerender } = typed("1500");

    rerender({ text: "1500," });
    expect(result.current).toBe(1500);

    rerender({ text: "1500,5" });
    expect(result.current).toBe(1500.5);
  });

  it("lets the amount go when the field is cleared", () => {
    const { result, rerender } = typed("1500");

    rerender({ text: " " });

    expect(result.current).toBeNull();
  });

  it("has no amount until one can be accepted", () => {
    expect(typed("1500abc").result.current).toBeNull();
  });
});
