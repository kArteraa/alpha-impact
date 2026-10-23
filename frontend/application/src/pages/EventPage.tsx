import { InsightPanel } from "@alpha-impact/plugin";
import { Link, useParams } from "react-router";
import { useCompany } from "../company/context";
import { FeedStatus } from "../dashboard/FeedStatus";
import { DASHBOARD } from "../feed/context";
import { useSession } from "../session/context";

export function EventPage() {
  const { id } = useParams();
  const { company } = useCompany();
  const { role } = useSession();
  return (
    <section>
      <div className="page-head">
        <Link to="/events">Все события</Link>
        <h1>Событие</h1>
        <p className="page-sub">{company.name}</p>
      </div>
      <FeedStatus empty={<p className="empty">Пока ничего важного для вашего бизнеса</p>}>
        {(events) => {
          const card = events.find((event) => event.id === id);
          if (card === undefined) {
            return (
              <div className="card empty-state">
                <h2>Событие больше не в ленте</h2>
                <p className="muted">Лента обновилась, а это событие в неё больше не входит.</p>
              </div>
            );
          }
          return <InsightPanel actionContext={DASHBOARD} role={role} response={{ silent: false, cards: [card] }} />;
        }}
      </FeedStatus>
    </section>
  );
}
