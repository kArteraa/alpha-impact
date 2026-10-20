import type { Feature } from "@alpha-impact/plugin";
import { describe, expect, it } from "vitest";
import { editFeature, formatFeatureValue, isEditable } from "./editFeature";

const bankFact: Feature = { value: "Оптовая торговля", source: "bank", confidence: 1, updated_at: "2026-10-01T00:00:00Z" };
const derived: Feature = { value: true, source: "inferred", confidence: 0.7, updated_at: "2026-10-01T00:00:00Z" };

describe("profile features", () => {
  it("lets the client edit derived traits but not bank facts", () => {
    expect(isEditable(bankFact)).toBe(false);
    expect(isEditable(derived)).toBe(true);
    expect(isEditable({ ...derived, source: "graph" })).toBe(true);
    expect(isEditable({ ...derived, source: "user" })).toBe(true);
  });

  it("stores the edit as the client's own value", () => {
    const features = { industry: bankFact, leasing: derived };
    const edited = editFeature(features, "leasing", "нет, парк собственный");

    expect(edited.leasing.value).toBe("нет, парк собственный");
    expect(edited.leasing.source).toBe("user");
    expect(edited.industry).toBe(bankFact);
    expect(features.leasing).toBe(derived);
  });

  it("refuses to edit a bank fact", () => {
    expect(() => editFeature({ industry: bankFact }, "industry", "Розница")).toThrow();
  });

  it.each([
    [true, "да"],
    [false, "нет"],
    [["юани", "дирхамы"], "юани, дирхамы"],
    [43, "43"],
    [null, "—"],
    ["крупный", "крупный"],
  ] as const)("shows %j as %s", (value, text) => {
    expect(formatFeatureValue(value as Feature["value"])).toBe(text);
  });
});
