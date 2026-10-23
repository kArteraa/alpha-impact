import { type InsightCard, significanceLevel } from "@alpha-impact/plugin";
import { rankEvents } from "./rankEvents";

export interface EventGroup {
  level: number;
  events: InsightCard[];
}

export function groupBySignificance(events: InsightCard[]): EventGroup[] {
  const groups: EventGroup[] = [];
  for (const event of rankEvents(events)) {
    const level = significanceLevel(event.significance);
    const last = groups[groups.length - 1];
    if (last?.level === level) {
      last.events.push(event);
    } else {
      groups.push({ level, events: [event] });
    }
  }
  return groups;
}
