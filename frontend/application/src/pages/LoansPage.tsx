import { useId } from "react";
import { LOANS } from "../data/loans";
import { RUB_WHOLE } from "../money";

const DATE = new Intl.DateTimeFormat("ru-RU", { timeZone: "UTC" });

export function LoansPage() {
  const titleId = useId();
  return (
    <section>
      <h1>Кредиты</h1>
      <div className="card">
        <div className="table-head">
          <h2 id={titleId}>Кредитный портфель</h2>
          <button type="button" className="button">
            Новый транш
          </button>
        </div>
        <table className="portfolio" aria-labelledby={titleId}>
          <thead>
            <tr>
              <th scope="col">Продукт</th>
              <th scope="col" className="number">
                Сумма
              </th>
              <th scope="col">Ставка</th>
              <th scope="col">Погашение</th>
            </tr>
          </thead>
          <tbody>
            {LOANS.map((loan) => (
              <tr key={loan.id}>
                <td>{loan.product}</td>
                <td className="number">{RUB_WHOLE.format(loan.amount)}</td>
                <td>{loan.rate}</td>
                <td>{DATE.format(new Date(loan.maturity))}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
