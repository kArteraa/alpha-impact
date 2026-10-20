import { InsightPanel, useInterpret } from "@alpha-impact/plugin";
import { type FormEvent, useId, useState } from "react";
import { COUNTERPARTIES } from "../data/counterparties";
import { formatRub, parseAmount } from "../money";
import { mockInterpret } from "../payment/mockInterpret";
import { type PaymentForm, paymentContextOf, toPaymentContext } from "../payment/paymentContext";

const EMPTY_FORM: PaymentForm = { beneficiaryId: "", amount: "", purpose: "" };

export function PaymentPage() {
  const recipientHintId = useId();
  const amountHintId = useId();
  const [form, setForm] = useState<PaymentForm>(EMPTY_FORM);
  const [heldAmount, setHeldAmount] = useState<number | null>(null);
  const paymentContext = toPaymentContext(form);
  const panelContext = paymentContextOf(form.beneficiaryId, heldAmount);
  const insight = useInterpret(panelContext, mockInterpret);
  const recipient = COUNTERPARTIES.find((counterparty) => counterparty.id === form.beneficiaryId);
  const amountInvalid = form.amount.trim() !== "" && parseAmount(form.amount) === null;

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
            <label htmlFor={`${recipientHintId}-select`} className="muted">
              Получатель
            </label>
            <select
              id={`${recipientHintId}-select`}
              value={form.beneficiaryId}
              aria-describedby={recipient ? recipientHintId : undefined}
              onChange={(event) => update("beneficiaryId", event.target.value)}
            >
              <option value="">Выберите контрагента</option>
              {COUNTERPARTIES.map((counterparty) => (
                <option key={counterparty.id} value={counterparty.id}>
                  {counterparty.name}
                </option>
              ))}
            </select>
            {recipient && (
              <small id={recipientHintId} className="field-hint">
                {recipient.description}
              </small>
            )}
          </div>
          <div className="field">
            <label htmlFor={`${amountHintId}-input`} className="muted">
              Сумма, ₽
            </label>
            <input
              id={`${amountHintId}-input`}
              inputMode="decimal"
              placeholder="0"
              value={form.amount}
              aria-invalid={amountInvalid}
              aria-describedby={amountInvalid ? amountHintId : undefined}
              onChange={(event) => updateAmount(event.target.value)}
              onBlur={() => update("amount", formatRub(form.amount))}
            />
            {amountInvalid && (
              <small id={amountHintId} className="field-hint">
                Сумма — положительное число, не больше двух знаков после запятой
              </small>
            )}
          </div>
          <label className="field">
            <span className="muted">Назначение платежа</span>
            <textarea rows={3} value={form.purpose} onChange={(event) => update("purpose", event.target.value)} />
          </label>
          <button className="button" type="submit" disabled={paymentContext === null}>
            Отправить
          </button>
        </form>
        <aside>
          {panelContext ? (
            <InsightPanel
              actionContext={panelContext}
              role="cfo"
              response={insight.response}
              pending={insight.pending}
              failed={insight.failed}
              onRetry={insight.retry}
            />
          ) : (
            <div className="card muted">Выберите получателя и сумму — Alpha Impact проверит, что важно для этого платежа</div>
          )}
        </aside>
      </div>
    </section>
  );
}
