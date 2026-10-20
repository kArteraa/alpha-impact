import { Link } from "react-router";
import { useCompany } from "../company/context";
import { EventSummary } from "../dashboard/EventSummary";
import { rankEvents } from "../dashboard/rankEvents";
import { EVENTS } from "../data/events";

export function EventsPage() {
  const { company } = useCompany();
  const events = rankEvents(EVENTS[company.id] ?? []);
  return (
    <section>
      <h1>Все события</h1>
      <div className="card">
        {events.length === 0 ? (
          <p className="empty">
            Пока ничего важного для вашего бизнеса. <Link to="/">На главную</Link>
          </p>
        ) : (
          <ul key={company.id} className="events appear">
            {events.map((event) => (
              <EventSummary key={event.id} event={event} />
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
