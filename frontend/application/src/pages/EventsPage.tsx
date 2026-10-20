import { Link } from "react-router";
import { EventList } from "../dashboard/EventList";

export function EventsPage() {
  return (
    <section>
      <h1>Все события</h1>
      <div className="card">
        <EventList
          empty={
            <>
              Пока ничего важного для вашего бизнеса. <Link to="/">На главную</Link>
            </>
          }
        />
      </div>
    </section>
  );
}
