import { SIGNIFICANCE_LEVELS } from "@alpha-impact/plugin";
import { useId } from "react";
import { Link } from "react-router";
import { useCompany } from "../company/context";
import { EventSummary } from "../dashboard/EventSummary";
import { FeedStatus } from "../dashboard/FeedStatus";
import { type EventGroup, groupBySignificance } from "../dashboard/groupEvents";
import { useFeed } from "../feed/context";
import { Icon } from "../ui/Icon";
import { plural } from "../ui/plural";

const LEVEL_TITLES: Record<number, string> = {
  3: "Высокая значимость",
  2: "Средняя значимость",
  1: "Низкая значимость",
};

const EVENT_FORMS = { one: "событие", few: "события", many: "событий" };

function Group({ group }: { group: EventGroup }) {
  const headingId = useId();
  return (
    <section className="card event-group" data-level={group.level} aria-labelledby={headingId}>
      <div className="event-group-head">
        <h2 id={headingId}>{LEVEL_TITLES[group.level]}</h2>
        <span className={group.level === SIGNIFICANCE_LEVELS ? "badge badge-danger" : "badge"}>{group.events.length}</span>
      </div>
      <ul className="events">
        {group.events.map((event) => (
          <EventSummary key={event.id} event={event} />
        ))}
      </ul>
    </section>
  );
}

export function EventsPage() {
  const { company } = useCompany();
  const { response } = useFeed();
  return (
    <section>
      <div className="page-head">
        <h1>Все события</h1>
        <p className="page-sub">
          <span>{company.name}</span>
          {response && <> · {plural(response.cards?.length ?? 0, EVENT_FORMS)}</>}
        </p>
      </div>
      <FeedStatus
        empty={
          <div className="card empty-state">
            <span className="check-mark" aria-hidden="true">
              <Icon name="check" size={24} />
            </span>
            <h2>Пока ничего важного</h2>
            <p className="muted">
              Alpha Impact следит за новостями и позицией банка по признакам компании и сообщит, когда что-то коснётся
              вашего бизнеса.
            </p>
            <Link to="/profile">Проверить профиль компании</Link>
          </div>
        }
      >
        {(events) => (
          <div className="event-groups">
            {groupBySignificance(events).map((group) => (
              <Group key={group.level} group={group} />
            ))}
          </div>
        )}
      </FeedStatus>
    </section>
  );
}
