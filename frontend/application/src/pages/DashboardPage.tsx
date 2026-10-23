import { useId } from "react";
import { Link } from "react-router";
import { AccountTile } from "../dashboard/AccountTile";
import { CashflowCard } from "../dashboard/CashflowCard";
import { EventSummary } from "../dashboard/EventSummary";
import { FeedStatus } from "../dashboard/FeedStatus";
import { DEPOSIT_RATES } from "../data/depositRates";
import { LOANS, LOANS_TOTAL } from "../data/loans";
import { RATE, RUB_WHOLE } from "../money";
import { Icon, type IconName } from "../ui/Icon";
import { plural } from "../ui/plural";

const WIDGET_EVENTS = 3;

const PRODUCTS = { one: "продукт", few: "продукта", many: "продуктов" };

const BEST_RATE = Math.max(...Object.values(DEPOSIT_RATES));

const TILE_META: Record<string, readonly [string, string]> = {
  "/deposits/new": [`до ${RATE.format(BEST_RATE)}%`, "годовых · демо-ставки"],
  "/loans": [RUB_WHOLE.format(LOANS_TOTAL), `в портфеле · ${plural(LOANS.length, PRODUCTS)}`],
};

const QUICK_ACTIONS: readonly (readonly [string, string, string, IconName, string])[] = [
  ["/payments/new", "Платёж", "Контрагенту по реквизитам", "payment", "tile-pay"],
  ["/deposits/new", "Депозит", "Разместить свободные средства", "deposit", "tile-deposit tile-side"],
  ["/loans", "Кредиты", "Портфель и новый транш", "loans", "tile-loans tile-side"],
];

export function DashboardPage() {
  const headingId = useId();
  return (
    <section>
      <h1 className="visually-hidden">Главный экран</h1>
      <div className="dashboard-grid">
        <section className="card feed-widget" aria-labelledby={headingId}>
          <div className="feed-head">
            <h2 id={headingId}>Что изменилось вокруг ваших операций</h2>
            <div className="feed-actions">
              <Link to="/news/new" className="button-primary button-xs">
                <Icon name="plus" />
                Вставить новость
              </Link>
              <Link to="/events">Все события</Link>
            </div>
          </div>
          <FeedStatus
            empty={
              <p className="empty">
                Пока ничего важного для вашего бизнеса. <Link to="/profile">Проверить профиль компании</Link>
              </p>
            }
          >
            {(events) => (
              <ul className="events appear">
                {events.slice(0, WIDGET_EVENTS).map((event) => (
                  <EventSummary key={event.id} event={event} />
                ))}
              </ul>
            )}
          </FeedStatus>
        </section>
        <AccountTile />
        <CashflowCard />
        <nav className="quick-actions" aria-label="Быстрые действия">
          {QUICK_ACTIONS.map(([to, title, caption, icon, tile]) => (
            <Link key={to} to={to} className={`card quick-action ${tile}`}>
              <span className="quick-icon">
                <Icon name={icon} size={24} />
              </span>
              <span className="quick-text">
                <strong>{title}</strong>
                <span className="muted">{caption}</span>
              </span>
              {TILE_META[to] && (
                <span className="quick-meta">
                  <span className="quick-meta-value">{TILE_META[to][0]}</span>
                  <span className="muted">{TILE_META[to][1]}</span>
                </span>
              )}
              <Icon name="arrow-right" className="quick-arrow" />
            </Link>
          ))}
        </nav>
      </div>
    </section>
  );
}
