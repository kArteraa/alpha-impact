import { describe, expect, it } from "vitest";
import { TRACES } from "../data/trace";
import { traceSummary } from "./summary";

describe("traceSummary", () => {
  const summary = traceSummary(TRACES["trace-mock-1"].steps);

  it("adds up the time and the tokens of the steps", () => {
    expect(summary.durationMs).toBe(3_510);
    expect(summary.tokensIn).toBe(5_830);
    expect(summary.tokensOut).toBe(790);
  });

  it("names every model once in the order of use", () => {
    expect(summary.models).toEqual(["Qwen3.6 35B A3B", "GLM-5.3-Flash"]);
  });

  it("splits the time between the models, the search and the service steps", () => {
    expect(summary.parts).toEqual([
      { kind: "model", durationMs: 3_150 },
      { kind: "tool", durationMs: 310 },
      { kind: "service", durationMs: 50 },
    ]);
  });

  it("measures the response time from the first start to the last finish", () => {
    const steps = TRACES["trace-mock-1"].steps;
    const overlapping = [
      { ...steps[0], started_at: "2026-10-20T10:15:00.000Z", duration_ms: 500 },
      { ...steps[1], started_at: "2026-10-20T10:15:00.100Z", duration_ms: 500 },
      { ...steps[2], started_at: "2026-10-20T10:15:01.100Z", duration_ms: 200 },
    ];

    expect(traceSummary(overlapping).durationMs).toBe(1_300);
  });

  it("is empty without steps", () => {
    expect(traceSummary([])).toEqual({ durationMs: 0, tokensIn: 0, tokensOut: 0, models: [], parts: [] });
  });
});
