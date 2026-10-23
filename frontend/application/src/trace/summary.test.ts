import { describe, expect, it } from "vitest";
import { traceSummary } from "./summary";
import { TRACE } from "./trace.fixture";

describe("traceSummary", () => {
  const summary = traceSummary(TRACE.steps);

  it("adds up the time, the tokens and the cost of the steps", () => {
    expect(summary.durationMs).toBe(21_980);
    expect(summary.tokensIn).toBe(28_832);
    expect(summary.tokensOut).toBe(2_536);
    expect(summary.costRub).toBeCloseTo(0.53);
  });

  it("names every model once in the order of use", () => {
    expect(summary.models).toEqual(["z-ai/glm-5.3-flash"]);
  });

  it("counts the critic that spent tokens as model time", () => {
    expect(summary.parts).toEqual([
      { kind: "model", durationMs: 21_900 },
      { kind: "tool", durationMs: 35 },
      { kind: "service", durationMs: 45 },
    ]);
  });

  it("measures the response time from the first start to the last finish", () => {
    const steps = TRACE.steps;
    const overlapping = [
      { ...steps[0], started_at: "2026-10-20T10:15:00.000Z", duration_ms: 500 },
      { ...steps[1], started_at: "2026-10-20T10:15:00.100Z", duration_ms: 500 },
      { ...steps[2], started_at: "2026-10-20T10:15:01.100Z", duration_ms: 200 },
    ];

    expect(traceSummary(overlapping).durationMs).toBe(1_300);
  });

  it("is empty without steps", () => {
    expect(traceSummary([])).toEqual({ durationMs: 0, tokensIn: 0, tokensOut: 0, costRub: 0, models: [], parts: [] });
  });
});
