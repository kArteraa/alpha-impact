import { useId } from "react";
import { Link } from "react-router";
import { useCompany } from "../company/CompanyContext";
import { EventSummary } from "../dashboard/EventSummary";
import { rankEvents } from "../dashboard/rankEvents";
import { EVENTS } from "../data/events";

const WIDGET_EVENTS = 3;

const QUICK_ACTIONS = [
  ["/payments/new", "Платёж", "Контрагенту по реквизитам"],
  ["/deposits/new", "Депозит", "Разместить свободные средства"],
  ["/loans", "Кредиты", "Портфель и новый транш"],
] as const;

const RUB = new Intl.NumberFormat("ru-RU", { style: "currency", currency: "RUB" });

export function DashboardPage() {
  const { company } = useCompany();
  const headingId = useId();
  const events = rankEvents(EVENTS[company.id] ?? []).slice(0, WIDGET_EVENTS);
  return (
    <section>
      <h1>Главный экран</h1>
      <div className="dashboard-grid">
        <section className="card feed-widget" aria-labelledby={headingId}>
          <div className="feed-head">
            <h2 id={headingId}>Что важно для вашего бизнеса</h2>
            <Link to="/events">Все события</Link>
          </div>
          {events.length === 0 ? (
            <p className="empty">
              Пока ничего важного для вашего бизнеса. <Link to="/profile">Проверить профиль компании</Link>
            </p>
          ) : (
            <ul key={company.id} className="events appear">
              {events.map((event) => (
                <EventSummary key={event.id} event={event} />
              ))}
            </ul>
          )}
        </section>
        <div className="card account">
          <span className="muted">Расчётный счёт {company.account}</span>
          <strong className="balance">{RUB.format(company.balance)}</strong>
          <span className="muted">Доступно сегодня</span>
        </div>
        <nav className="quick-actions" aria-label="Быстрые действия">
          {QUICK_ACTIONS.map(([to, title, caption]) => (
            <Link key={to} to={to} className="card quick-action">
              <strong>{title}</strong>
              <span className="muted">{caption}</span>
            </Link>
          ))}
        </nav>
      </div>
    </section>
  );
}
