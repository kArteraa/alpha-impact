import type { ReactNode } from "react";
import { useCompany } from "../company/context";
import { EVENTS } from "../data/events";
import { EventSummary } from "./EventSummary";
import { rankEvents } from "./rankEvents";

export function EventList({ limit, empty }: { limit?: number; empty: ReactNode }) {
  const { company } = useCompany();
  const events = rankEvents(EVENTS[company.id] ?? []).slice(0, limit);
  if (events.length === 0) {
    return <p className="empty">{empty}</p>;
  }
  return (
    <ul key={company.id} className="events appear">
      {events.map((event) => (
        <EventSummary key={event.id} event={event} />
      ))}
    </ul>
  );
}
