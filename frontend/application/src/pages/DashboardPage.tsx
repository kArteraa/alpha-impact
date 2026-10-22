import { useId } from "react";
import { Link } from "react-router";
import { useCompany } from "../company/context";
import { EventList } from "../dashboard/EventList";
import { DEPOSIT_RATES } from "../data/depositRates";
import { LOANS, LOANS_TOTAL } from "../data/loans";
import { RATE, RUB_WHOLE } from "../money";
import { Amount } from "../ui/Amount";
import { Icon, type IconName } from "../ui/Icon";

const WIDGET_EVENTS = 3;

const PLURAL = new Intl.PluralRules("ru-RU");
const PRODUCT_FORMS: Record<Intl.LDMLPluralRule, string> = {
  zero: "продуктов",
  one: "продукт",
  two: "продукта",
  few: "продукта",
  many: "продуктов",
  other: "продукта",
};
const products = (count: number) => `${count} ${PRODUCT_FORMS[PLURAL.select(count)]}`;

const BEST_RATE = Math.max(...Object.values(DEPOSIT_RATES));

const TILE_META: Record<string, readonly [string, string]> = {
  "/deposits/new": [`до ${RATE.format(BEST_RATE)}%`, "годовых · демо-ставки"],
  "/loans": [RUB_WHOLE.format(LOANS_TOTAL), `в портфеле · ${products(LOANS.length)}`],
};

const QUICK_ACTIONS: readonly (readonly [string, string, string, IconName, string])[] = [
  ["/payments/new", "Платёж", "Контрагенту по реквизитам", "payment", "tile-pay"],
  ["/deposits/new", "Депозит", "Разместить свободные средства", "deposit", "tile-deposit"],
  ["/loans", "Кредиты", "Портфель и новый транш", "loans", "tile-loans"],
];

export function DashboardPage() {
  const { company } = useCompany();
  const headingId = useId();
  return (
    <section>
      <h1 className="visually-hidden">Главный экран</h1>
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
          <div className="account-head">
            <span className="account-label">Расчётный счёт</span>
            <span className="account-number">{company.account}</span>
          </div>
          <div className="account-body">
            <span className="account-caption">Доступно сегодня</span>
            <Amount className="account-amount" value={company.balance} />
          </div>
        </div>
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
