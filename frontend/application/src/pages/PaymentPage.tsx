import { type FormEvent, useId, useState } from "react";
import { COUNTERPARTIES } from "../data/counterparties";
import { ActionPanel } from "../insight/ActionPanel";
import { PanelPlaceholder } from "../insight/PanelPlaceholder";
import { amountError, parseAmount } from "../money";
import { type PaymentForm, paymentContextOf, toPaymentContext } from "../payment/paymentContext";
import { AmountField } from "../ui/AmountField";
import { Select } from "../ui/Select";
import { useHeldAmount } from "../ui/useHeldAmount";

const RECIPIENTS = COUNTERPARTIES.map((counterparty) => ({
  value: counterparty.id,
  label: counterparty.name,
  hint: counterparty.description,
}));

const EMPTY_FORM: PaymentForm = { beneficiaryId: "", amount: "", purpose: "" };

export function PaymentPage() {
  const recipientHintId = useId();
  const [form, setForm] = useState<PaymentForm>(EMPTY_FORM);
  const heldAmount = useHeldAmount(form.amount);
  const paymentContext = toPaymentContext(form);
  const recipient = COUNTERPARTIES.find((counterparty) => counterparty.id === form.beneficiaryId);
  const amount = parseAmount(form.amount);

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
            error={amountError(form.amount)}
            onChange={(value) => update("amount", value)}
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
          <ActionPanel
            context={paymentContextOf(form.beneficiaryId, heldAmount)}
            placeholder={
              <PanelPlaceholder
                title="Проверка платежа"
                text="Выберите получателя и сумму — Alpha Impact покажет новости и позицию банка, которые касаются этого платежа"
                steps={[
                  ["Получатель", recipient !== undefined],
                  ["Сумма", amount !== null],
                ]}
              />
            }
          />
        </aside>
      </div>
    </section>
  );
}
