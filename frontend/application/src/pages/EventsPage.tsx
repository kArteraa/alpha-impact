import { Link } from "react-router";
import { useCompany } from "../company/context";
import { EventList } from "../dashboard/EventList";

export function EventsPage() {
  const { company } = useCompany();
  return (
    <section>
      <div className="page-head">
        <h1>Все события</h1>
        <p className="page-sub">{company.name}</p>
      </div>
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
