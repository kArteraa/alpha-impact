import type { InsightCard } from "@alpha-impact/plugin";

export function rankEvents(events: InsightCard[]): InsightCard[] {
  return [...events].sort((left, right) => right.significance - left.significance);
}
