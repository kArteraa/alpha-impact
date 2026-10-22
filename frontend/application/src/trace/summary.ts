import type { TraceStep } from "@alpha-impact/plugin";

export type StepKind = "model" | "tool" | "service";

export interface TracePart {
  kind: StepKind;
  durationMs: number;
}

export interface TraceSummary {
  durationMs: number;
  tokensIn: number;
  tokensOut: number;
  models: string[];
  parts: TracePart[];
}

const KINDS: readonly StepKind[] = ["model", "tool", "service"];

function kindOf(step: TraceStep): StepKind {
  if (step.model) {
    return "model";
  }
  return step.step === "tool" ? "tool" : "service";
}

export function traceSummary(steps: readonly TraceStep[]): TraceSummary {
  const byKind = new Map<StepKind, number>();
  for (const step of steps) {
    const kind = kindOf(step);
    byKind.set(kind, (byKind.get(kind) ?? 0) + (step.duration_ms ?? 0));
  }
  return {
    durationMs: steps.reduce((sum, step) => sum + (step.duration_ms ?? 0), 0),
    tokensIn: steps.reduce((sum, step) => sum + (step.tokens_in ?? 0), 0),
    tokensOut: steps.reduce((sum, step) => sum + (step.tokens_out ?? 0), 0),
    models: [...new Set(steps.flatMap((step) => (step.model ? [step.model] : [])))],
    parts: KINDS.filter((kind) => byKind.has(kind)).map((kind) => ({ kind, durationMs: byKind.get(kind) ?? 0 })),
  };
}
