import type { InsightCard } from "@alpha-impact/plugin";
import { describe, expect, it } from "vitest";
import { rankEvents } from "./rankEvents";

function event(id: string, significance: number): InsightCard {
  return {
    id,
    headline: id,
    significance,
    trace_id: `trace-${id}`,
    what_happened: [],
    why_for_you: [],
    consequences: [],
    actions: [],
    bank_view: [],
    basis: [],
  };
}

describe("rankEvents", () => {
  it("puts the most significant events first", () => {
    const ranked = rankEvents([event("low", 0.2), event("high", 0.9), event("mid", 0.5)]);
    expect(ranked.map((card) => card.id)).toEqual(["high", "mid", "low"]);
  });

  it("does not reorder the source list", () => {
    const events = [event("low", 0.2), event("high", 0.9)];
    rankEvents(events);
    expect(events.map((card) => card.id)).toEqual(["low", "high"]);
  });
});
