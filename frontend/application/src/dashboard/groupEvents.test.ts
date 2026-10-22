import type { InsightCard } from "@alpha-impact/plugin";
import { describe, expect, it } from "vitest";
import { groupBySignificance } from "./groupEvents";

function event(id: string, significance: number): InsightCard {
  return {
    id,
    headline: id,
    significance,
    trace_id: "trace",
    why_for_you: [],
    what_happened: [],
    consequences: [],
    actions: [],
    bank_view: [],
    basis: [],
  };
}

describe("groupBySignificance", () => {
  it("puts the most significant group first and ranks events inside", () => {
    const groups = groupBySignificance([event("a", 0.4), event("b", 0.9), event("c", 0.7), event("d", 0.8)]);

    expect(groups.map((group) => [group.level, group.events.map((item) => item.id)])).toEqual([
      [3, ["b", "d", "c"]],
      [2, ["a"]],
    ]);
  });

  it("skips empty levels", () => {
    expect(groupBySignificance([event("a", 0.1)]).map((group) => group.level)).toEqual([1]);
  });

  it("has no groups without events", () => {
    expect(groupBySignificance([])).toEqual([]);
  });
});
