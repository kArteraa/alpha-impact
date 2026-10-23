import { useId, useState } from "react";
import { DEPOSIT_RATES } from "../data/depositRates";
import { DEPOSIT_TERMS, type DepositTerm, depositIncome } from "../deposit/calc";
import { parseAmount, RATE, RUB_COMPACT } from "../money";
import { AmountField } from "../ui/AmountField";
import { Columns, type ColumnSeries } from "../ui/charts/Columns";
import { Amount } from "../ui/Amount";

const DEFAULT_TERM: DepositTerm = 6;

const formatRate = (value: number) => `${RATE.format(value)}%`;

const TERM_SERIES: readonly ColumnSeries[] = [{ name: "Срок", tone: "primary" }];

export function DepositPage() {
  const termLabelId = useId();
  const [amountText, setAmountText] = useState("");
  const [term, setTerm] = useState<DepositTerm>(DEFAULT_TERM);
  const amount = parseAmount(amountText);
  const rate = DEPOSIT_RATES[term];
  return (
    <section>
      <h1>Новый депозит</h1>
      <div className="page-grid">
        <form className="card form" onSubmit={(event) => event.preventDefault()}>
          <h2>Разместить средства</h2>
          <AmountField label="Сумма" value={amountText} onChange={setAmountText} />
          <div className="field field-static">
            <span className="muted" id={termLabelId}>
              Срок
            </span>
            <div className="segmented" role="radiogroup" aria-labelledby={termLabelId}>
              {DEPOSIT_TERMS.map((option) => (
                <label key={option}>
                  <input
                    type="radio"
                    name={termLabelId}
                    checked={option === term}
                    onChange={() => setTerm(option)}
                  />
                  <span>{option} мес.</span>
                </label>
              ))}
            </div>
          </div>
        </form>
        <aside className="card deposit-result">
          <div className="deposit-now" aria-live="polite">
            <span className="muted">Доход за {term} мес.</span>
            {amount === null ? (
              <p className="empty">Введите сумму — посчитаю доход за выбранный срок</p>
            ) : (
              <Amount className="amount-lg" testId="deposit-income" value={depositIncome(amount, term, rate)} />
            )}
            <div className="deposit-meta">
              <span className="badge">{RATE.format(rate)}% годовых</span>
              <span className="badge badge-warning">демо-ставки</span>
            </div>
          </div>
          <div className="deposit-terms">
            <span className="muted">{amount === null ? "Ставка по сроку" : "Доход по сроку"}</span>
            <Columns
              title={amount === null ? "Ставка по сроку, % годовых" : "Доход по сроку"}
              series={TERM_SERIES}
              groups={DEPOSIT_TERMS.map((option) => ({
                label: `${option} мес.`,
                values: [amount === null ? DEPOSIT_RATES[option] : depositIncome(amount, option, DEPOSIT_RATES[option])],
                active: option === term,
              }))}
              format={amount === null ? formatRate : (value) => RUB_COMPACT.format(value)}
              showValues
            />
          </div>
        </aside>
      </div>
    </section>
  );
}
