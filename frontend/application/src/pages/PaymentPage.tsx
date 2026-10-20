import { InsightPanel, type InterpretResponse, mockResponses } from "@alpha-impact/plugin";
import { type FormEvent, useState } from "react";
import { COUNTERPARTIES } from "../data/counterparties";
import { type PaymentForm, toPaymentContext } from "../payment/paymentContext";

const DEMO_CARDS_COUNTERPARTY = "cp_logistics_spb";

const EMPTY_FORM: PaymentForm = { beneficiaryId: "", amount: "", purpose: "" };

function mockResponseFor(beneficiaryId: string): InterpretResponse {
  return beneficiaryId === DEMO_CARDS_COUNTERPARTY ? mockResponses.cards : mockResponses.silent;
}

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
          <label className="field">
            <span>Получатель</span>
            <select value={form.beneficiaryId} onChange={(event) => update("beneficiaryId", event.target.value)}>
              <option value="">Выберите контрагента</option>
              {COUNTERPARTIES.map((counterparty) => (
                <option key={counterparty.id} value={counterparty.id}>
                  {counterparty.name}
                </option>
              ))}
            </select>
            {recipient && <small>{recipient.description}</small>}
          </label>
          <label className="field">
            <span>Сумма, ₽</span>
            <input
              inputMode="decimal"
              placeholder="0"
              value={form.amount}
              onChange={(event) => update("amount", event.target.value)}
            />
          </label>
          <label className="field">
            <span>Назначение платежа</span>
            <textarea rows={3} value={form.purpose} onChange={(event) => update("purpose", event.target.value)} />
          </label>
          <button className="button button-primary" type="submit" disabled={paymentContext === null}>
            Продолжить
          </button>
        </form>
        <aside className="insight-slot">
          {paymentContext ? (
            <InsightPanel
              actionContext={paymentContext}
              role="cfo"
              response={mockResponseFor(form.beneficiaryId)}
            />
          ) : (
            <div className="card hint">Выберите получателя и сумму — Alpha Impact проверит, что важно для этого платежа</div>
          )}
        </aside>
      </div>
    </section>
  );
}
