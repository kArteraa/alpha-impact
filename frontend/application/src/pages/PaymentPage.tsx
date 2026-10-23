import { InsightPanel, type InterpretFetcher, useInterpret } from "@alpha-impact/plugin";
import { type FormEvent, useCallback, useId, useState } from "react";
import { api } from "../api/client";
import { useCompany } from "../company/context";
import { COUNTERPARTIES } from "../data/counterparties";
import { parseAmount } from "../money";
import { PanelPlaceholder } from "../payment/PanelPlaceholder";
import { type PaymentForm, paymentContextOf, toPaymentContext } from "../payment/paymentContext";
import { useSession } from "../session/context";
import { AmountField } from "../ui/AmountField";
import { Select } from "../ui/Select";

const AMOUNT_HINT = "Сумма — положительное число, не больше двух знаков после запятой";

const RECIPIENTS = COUNTERPARTIES.map((counterparty) => ({
  value: counterparty.id,
  label: counterparty.name,
  hint: counterparty.description,
}));

const EMPTY_FORM: PaymentForm = { beneficiaryId: "", amount: "", purpose: "" };

export function PaymentPage() {
  const { company } = useCompany();
  const { userId, role } = useSession();
  const recipientHintId = useId();
  const [form, setForm] = useState<PaymentForm>(EMPTY_FORM);
  const [heldAmount, setHeldAmount] = useState<number | null>(null);
  const paymentContext = toPaymentContext(form);
  const panelContext = paymentContextOf(form.beneficiaryId, heldAmount);
  const interpret = useCallback<InterpretFetcher>(
    (context, signal) => api.interpret({ user_id: userId, client_id: company.id, role, action_context: context }, signal),
    [userId, company.id, role],
  );
  const insight = useInterpret(panelContext, interpret);
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
            <Select
              label="Получатель"
              value={form.beneficiaryId}
              placeholder="Выберите контрагента"
              options={RECIPIENTS}
              describedBy={recipient ? recipientHintId : undefined}
              onChange={(value) => update("beneficiaryId", value)}
            />
            {recipient && (
              <small id={recipientHintId} className="field-hint">
                {recipient.description}
              </small>
            )}
          </div>
          <AmountField
            label="Сумма"
            value={form.amount}
            error={amountInvalid ? AMOUNT_HINT : null}
            onChange={updateAmount}
          />
          <label className="field field-static">
            <span className="muted">Назначение платежа</span>
            <textarea rows={3} value={form.purpose} onChange={(event) => update("purpose", event.target.value)} />
          </label>
          <div className="form-actions">
            <button className="button" type="submit" disabled={paymentContext === null}>
              Отправить
            </button>
          </div>
        </form>
        <aside>
          {panelContext ? (
            <InsightPanel
              actionContext={panelContext}
              role={role}
              response={insight.response}
              pending={insight.pending}
              failed={insight.failed}
              onRetry={insight.retry}
            />
          ) : (
            <PanelPlaceholder recipient={recipient !== undefined} amount={parseAmount(form.amount) !== null} />
          )}
        </aside>
      </div>
    </section>
  );
}
