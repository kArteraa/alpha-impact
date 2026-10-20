import type { InterpretFetcher } from "@alpha-impact/plugin";
import { mockInsightFor } from "./mockInsight";

export const mockInterpret: InterpretFetcher = (context) =>
  Promise.resolve(mockInsightFor("beneficiary_id" in context ? context.beneficiary_id : null));
