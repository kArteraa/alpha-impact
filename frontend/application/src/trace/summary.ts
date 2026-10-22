import type { TraceStep } from "@alpha-impact/plugin";

export type StepKind = "model" | "tool" | "service";

interface TracePart {
  kind: StepKind;
  durationMs: number;
}

interface TraceSummary {
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
  const models = new Set<string>();
  let durationMs = 0;
  let tokensIn = 0;
  let tokensOut = 0;
  for (const step of steps) {
    const duration = step.duration_ms ?? 0;
    const kind = kindOf(step);
    byKind.set(kind, (byKind.get(kind) ?? 0) + duration);
    durationMs += duration;
    tokensIn += step.tokens_in ?? 0;
    tokensOut += step.tokens_out ?? 0;
    if (step.model) {
      models.add(step.model);
    }
  }
  return {
    durationMs,
    tokensIn,
    tokensOut,
    models: [...models],
    parts: KINDS.filter((kind) => byKind.has(kind)).map((kind) => ({ kind, durationMs: byKind.get(kind) ?? 0 })),
  };
}
