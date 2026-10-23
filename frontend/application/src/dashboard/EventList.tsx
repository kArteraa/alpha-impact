import type { ReactNode } from "react";
import { EventSummary } from "./EventSummary";
import { FeedStatus } from "./FeedStatus";

export function EventList({ limit, empty }: { limit?: number; empty: ReactNode }) {
  return (
    <FeedStatus empty={<p className="empty">{empty}</p>}>
      {(events) => (
        <ul className="events appear">
          {events.slice(0, limit).map((event) => (
            <EventSummary key={event.id} event={event} />
          ))}
        </ul>
      )}
    </FeedStatus>
  );
}
