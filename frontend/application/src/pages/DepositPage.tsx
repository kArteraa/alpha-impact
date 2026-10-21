import { useId, useState } from "react";
import { DEPOSIT_RATES } from "../data/depositRates";
import { DEPOSIT_TERMS, type DepositTerm, depositIncome } from "../deposit/calc";
import { parseAmount } from "../money";
import { Amount } from "../ui/Amount";

const DEFAULT_TERM: DepositTerm = 6;
const RATE = new Intl.NumberFormat("ru-RU", { maximumFractionDigits: 2 });

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
          <label className="field">
            <span className="muted">Сумма, ₽</span>
            <input
              inputMode="decimal"
              placeholder="0"
              value={amountText}
              onChange={(event) => setAmountText(event.target.value)}
            />
          </label>
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
        <aside className="card deposit-result" aria-live="polite">
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
        </aside>
      </div>
    </section>
  );
}
