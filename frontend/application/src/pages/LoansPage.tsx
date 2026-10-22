import { useId } from "react";
import { LOANS, LOANS_TOTAL } from "../data/loans";
import { RUB_WHOLE } from "../money";
import { Icon } from "../ui/Icon";

const DATE = new Intl.DateTimeFormat("ru-RU", { timeZone: "UTC" });

const NEAREST = [...LOANS].sort((left, right) => left.maturity.localeCompare(right.maturity))[0];

export function LoansPage() {
  const titleId = useId();
  return (
    <section>
      <h1>Кредиты</h1>
      <div className="stats">
        <div className="card stat">
          <span className="muted">Общая сумма</span>
          <strong>{RUB_WHOLE.format(LOANS_TOTAL)}</strong>
        </div>
        <div className="card stat">
          <span className="muted">Продуктов</span>
          <strong>{LOANS.length}</strong>
        </div>
        <div className="card stat">
          <span className="muted">Ближайшее погашение</span>
          <strong>{DATE.format(new Date(NEAREST.maturity))}</strong>
          <span className="muted">{NEAREST.product}</span>
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
              </tr>
            </thead>
            <tbody>
              {LOANS.map((loan) => (
                <tr key={loan.id}>
                  <td>{loan.product}</td>
                  <td className="number">{RUB_WHOLE.format(loan.amount)}</td>
                  <td>{loan.rate}</td>
                  <td className="number">{DATE.format(new Date(loan.maturity))}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
