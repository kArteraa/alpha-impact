import { useId } from "react";
import { Link } from "react-router";
import { useCompany } from "../company/context";
import { EventList } from "../dashboard/EventList";
import { RUB } from "../money";

const WIDGET_EVENTS = 3;

const QUICK_ACTIONS = [
  ["/payments/new", "Платёж", "Контрагенту по реквизитам"],
  ["/deposits/new", "Депозит", "Разместить свободные средства"],
  ["/loans", "Кредиты", "Портфель и новый транш"],
] as const;

export function DashboardPage() {
  const { company } = useCompany();
  const headingId = useId();
  return (
    <section>
      <h1>Главный экран</h1>
      <div className="dashboard-grid">
        <section className="card feed-widget" aria-labelledby={headingId}>
          <div className="feed-head">
            <h2 id={headingId}>Что важно для вашего бизнеса</h2>
            <Link to="/events">Все события</Link>
          </div>
          <EventList
            limit={WIDGET_EVENTS}
            empty={
              <>
                Пока ничего важного для вашего бизнеса. <Link to="/profile">Проверить профиль компании</Link>
              </>
            }
          />
        </section>
        <div className="card account">
          <span className="muted">Расчётный счёт {company.account}</span>
          <strong className="amount-lg">{RUB.format(company.balance)}</strong>
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
