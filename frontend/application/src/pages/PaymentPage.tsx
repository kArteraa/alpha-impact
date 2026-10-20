import { InsightPanel } from "@alpha-impact/plugin";
import { type FormEvent, useState } from "react";
import { COUNTERPARTIES } from "../data/counterparties";
import { mockInsightFor } from "../payment/mockInsight";
import { type PaymentForm, toPaymentContext } from "../payment/paymentContext";

const RECIPIENT_HINT_ID = "recipient-hint";

const EMPTY_FORM: PaymentForm = { beneficiaryId: "", amount: "", purpose: "" };

export function PaymentPage() {
  const [form, setForm] = useState<PaymentForm>(EMPTY_FORM);
  const paymentContext = toPaymentContext(form);
  const recipient = COUNTERPARTIES.find((counterparty) => counterparty.id === form.beneficiaryId);

  function update(field: keyof PaymentForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (paymentContext) {
      console.info("PaymentContext", paymentContext);
    }
  }

  return (
    <section>
      <h1>Новый платёж</h1>
      <div className="page-grid">
        <form className="card form" onSubmit={submit}>
          <h2>Платёж контрагенту</h2>
          <div className="field">
            <label className="field">
              <span className="muted">Получатель</span>
              <select
                value={form.beneficiaryId}
                aria-describedby={recipient ? RECIPIENT_HINT_ID : undefined}
                onChange={(event) => update("beneficiaryId", event.target.value)}
              >
                <option value="">Выберите контрагента</option>
                {COUNTERPARTIES.map((counterparty) => (
                  <option key={counterparty.id} value={counterparty.id}>
                    {counterparty.name}
                  </option>
                ))}
              </select>
            </label>
            {recipient && (
              <small id={RECIPIENT_HINT_ID} className="muted">
                {recipient.description}
              </small>
            )}
          </div>
          <label className="field">
            <span className="muted">Сумма, ₽</span>
            <input
              inputMode="decimal"
              placeholder="0"
              value={form.amount}
              onChange={(event) => update("amount", event.target.value)}
            />
          </label>
          <label className="field">
            <span className="muted">Назначение платежа</span>
            <textarea rows={3} value={form.purpose} onChange={(event) => update("purpose", event.target.value)} />
          </label>
          <button className="button" type="submit" disabled={paymentContext === null}>
            Продолжить
          </button>
        </form>
        <aside>
          {paymentContext ? (
            <InsightPanel
              actionContext={paymentContext}
              role="cfo"
              response={mockInsightFor(form.beneficiaryId)}
            />
          ) : (
            <div className="card muted">Выберите получателя и сумму — Alpha Impact проверит, что важно для этого платежа</div>
          )}
        </aside>
      </div>
    </section>
  );
}
