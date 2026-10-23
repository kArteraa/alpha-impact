import { useId, useState } from "react";
import { LOANS, LOANS_TOTAL } from "../data/loans";
import { daysUntil } from "../loans/maturity";
import { NewTranche } from "../loans/NewTranche";
import { PERCENT, RUB_WHOLE } from "../money";
import { ShareBar } from "../ui/charts/ShareBar";
import type { Tone } from "../ui/charts/tone";
import { Icon } from "../ui/Icon";
import { DAYS, plural } from "../ui/plural";

const DATE = new Intl.DateTimeFormat("ru-RU", { timeZone: "UTC" });
const SOON_DAYS = 90;
const TONES: readonly Tone[] = ["primary", "soft", "muted"];

const BY_MATURITY = [...LOANS].sort((left, right) => left.maturity.localeCompare(right.maturity));
const NEAREST = BY_MATURITY[0];
const BY_AMOUNT = [...LOANS].sort((left, right) => right.amount - left.amount);

function untilText(days: number): string {
  if (days < 0) {
    return `просрочено на ${plural(-days, DAYS)}`;
  }
  return days === 0 ? "сегодня" : `через ${plural(days, DAYS)}`;
}

function daysBadge(days: number): string {
  if (days < 0) {
    return "badge badge-danger";
  }
  return days <= SOON_DAYS ? "badge badge-warning" : "badge";
}

export function LoansPage() {
  const titleId = useId();
  const trancheId = useId();
  const [today] = useState(() => new Date());
  const [trancheOpen, setTrancheOpen] = useState(false);
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
          <div className="table-title">
            <h2 id={titleId}>Кредитный портфель</h2>
            <span className="badge badge-warning">демо-данные</span>
          </div>
          <button
            type="button"
            className="button-primary button-sm"
            aria-expanded={trancheOpen}
            aria-controls={trancheId}
            onClick={() => setTrancheOpen((open) => !open)}
          >
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
                      <span className={daysBadge(days)}>{days <= 0 ? untilText(days) : plural(days, DAYS)}</span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
      {trancheOpen && <NewTranche id={trancheId} />}
    </section>
  );
}
