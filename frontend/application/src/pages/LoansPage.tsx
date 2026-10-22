import { useId, useState } from "react";
import { LOANS, LOANS_TOTAL } from "../data/loans";
import { daysUntil } from "../loans/maturity";
import { PERCENT, RUB_WHOLE } from "../money";
import { ShareBar } from "../ui/charts/ShareBar";
import type { Tone } from "../ui/charts/tone";
import { Icon } from "../ui/Icon";
import { plural } from "../ui/plural";

const DATE = new Intl.DateTimeFormat("ru-RU", { timeZone: "UTC" });
const DAYS = { one: "день", few: "дня", many: "дней" };
const SOON_DAYS = 90;
const TONES: readonly Tone[] = ["primary", "soft", "muted"];

const BY_MATURITY = [...LOANS].sort((left, right) => left.maturity.localeCompare(right.maturity));
const NEAREST = BY_MATURITY[0];
const BY_AMOUNT = [...LOANS].sort((left, right) => right.amount - left.amount);

function untilText(days: number): string {
  return days > 0 ? `через ${plural(days, DAYS)}` : "сегодня";
}

export function LoansPage() {
  const titleId = useId();
  const [today] = useState(() => new Date());
  const nearestDays = daysUntil(NEAREST.maturity, today);
  return (
    <section>
      <h1>Кредиты</h1>
      <div className="loans-summary">
        <div className="card stat stat-main">
          <span className="muted">Общая сумма</span>
          <strong>{RUB_WHOLE.format(LOANS_TOTAL)}</strong>
          <ShareBar
            label="Структура портфеля"
            items={BY_AMOUNT.map((loan, index) => ({
              label: loan.product,
              value: loan.amount,
              tone: TONES[index % TONES.length],
              caption: `${RUB_WHOLE.format(loan.amount)} · ${PERCENT.format(loan.amount / LOANS_TOTAL)}`,
            }))}
          />
        </div>
        <div className="loans-side">
          <div className="card stat">
            <span className="muted">Продуктов</span>
            <strong>{LOANS.length}</strong>
          </div>
          <div className="card stat">
            <span className="muted">Ближайшее погашение</span>
            <strong>{DATE.format(new Date(NEAREST.maturity))}</strong>
            <span className="muted">
              {NEAREST.product} · {untilText(nearestDays)}
            </span>
          </div>
        </div>
      </div>
      <div className="card">
        <div className="table-head">
          <h2 id={titleId}>Кредитный портфель</h2>
          <button type="button" className="button-primary button-sm">
            <Icon name="plus" />
            Новый транш
          </button>
        </div>
        <div className="table-wrap">
          <table className="portfolio" aria-labelledby={titleId}>
            <thead>
              <tr>
                <th scope="col">Продукт</th>
                <th scope="col" className="number">
                  Сумма
                </th>
                <th scope="col">Ставка</th>
                <th scope="col" className="number">
                  Погашение
                </th>
                <th scope="col" className="number">
                  Осталось
                </th>
              </tr>
            </thead>
            <tbody>
              {BY_MATURITY.map((loan) => {
                const days = daysUntil(loan.maturity, today);
                return (
                  <tr key={loan.id}>
                    <td>{loan.product}</td>
                    <td className="number">{RUB_WHOLE.format(loan.amount)}</td>
                    <td>{loan.rate}</td>
                    <td className="number">{DATE.format(new Date(loan.maturity))}</td>
                    <td className="number">
                      <span className={days <= SOON_DAYS ? "badge badge-warning" : "badge"}>{plural(days, DAYS)}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
