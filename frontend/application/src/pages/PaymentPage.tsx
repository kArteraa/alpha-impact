import { InsightPanel } from "@alpha-impact/plugin";
import { type FormEvent, useMemo, useState } from "react";
import { COUNTERPARTIES } from "../data/counterparties";
import { mockInsightFor } from "../payment/mockInsight";
import { type PaymentForm, parseAmount, paymentContextOf, toPaymentContext } from "../payment/paymentContext";

const RECIPIENT_HINT_ID = "recipient-hint";

const EMPTY_FORM: PaymentForm = { beneficiaryId: "", amount: "", purpose: "" };

export function PaymentPage() {
  const [form, setForm] = useState<PaymentForm>(EMPTY_FORM);
  const paymentContext = toPaymentContext(form);
  const [heldAmount, setHeldAmount] = useState<number | null>(null);
  const panelContext = useMemo(() => paymentContextOf(form.beneficiaryId, heldAmount), [form.beneficiaryId, heldAmount]);
  const recipient = COUNTERPARTIES.find((counterparty) => counterparty.id === form.beneficiaryId);

  function update(field: keyof PaymentForm, value: string) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function updateAmount(value: string) {
    update("amount", value);
    const amount = parseAmount(value);
    if (value.trim() === "" || amount !== null) {
      setHeldAmount(amount);
    }
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
              onChange={(event) => updateAmount(event.target.value)}
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
          {panelContext ? (
            <InsightPanel
              actionContext={panelContext}
              role="cfo"
              response={mockInsightFor(panelContext.beneficiary_id)}
            />
          ) : (
            <div className="card muted">Выберите получателя и сумму — Alpha Impact проверит, что важно для этого платежа</div>
          )}
        </aside>
      </div>
    </section>
  );
}
