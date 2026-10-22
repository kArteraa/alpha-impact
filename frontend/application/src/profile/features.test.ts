import type { Feature } from "@alpha-impact/plugin";
import { describe, expect, it } from "vitest";
import { formatFeatureValue, isEditable } from "./features";

const bankFact: Feature = { value: "Оптовая торговля", source: "bank", confidence: 1, updated_at: "2026-10-01T00:00:00Z" };
const derived: Feature = { value: true, source: "inferred", confidence: 0.7, updated_at: "2026-10-01T00:00:00Z" };

describe("profile features", () => {
  it("lets the client edit derived traits but not bank facts", () => {
    expect(isEditable(bankFact)).toBe(false);
    expect(isEditable(derived)).toBe(true);
    expect(isEditable({ ...derived, source: "graph" })).toBe(true);
    expect(isEditable({ ...derived, source: "user" })).toBe(true);
  });

  it.each([
    [true, "да"],
    [false, "нет"],
    [["юани", "дирхамы"], "юани, дирхамы"],
    [43, "43"],
    [18_500_000_000, "18 500 000 000"],
    [null, "—"],
    ["крупный", "крупный"],
  ] as const)("shows %j as %s", (value, text) => {
    expect(formatFeatureValue(value as Feature["value"])).toBe(text);
  });
});
