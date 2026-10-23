import { useEffect, useId, useRef, useState } from "react";
import { LOANS } from "../data/loans";
import { ActionPanel } from "../insight/ActionPanel";
import { PanelPlaceholder } from "../insight/PanelPlaceholder";
import { parseAmount, RUB_WHOLE } from "../money";
import { AmountField } from "../ui/AmountField";
import { Select } from "../ui/Select";
import { useHeldAmount } from "../ui/useHeldAmount";
import { loanContextOf } from "./loanContext";

const PRODUCTS = LOANS.map((loan) => ({
  value: loan.id,
  label: loan.product,
  hint: `${loan.rate} · ${RUB_WHOLE.format(loan.amount)}`,
}));

export function NewTranche({ id }: { id: string }) {
  const headingId = useId();
  const heading = useRef<HTMLHeadingElement>(null);
  const [loanId, setLoanId] = useState("");
  const [amountText, setAmountText] = useState("");
  const heldAmount = useHeldAmount(amountText);
  const loan = LOANS.find((item) => item.id === loanId);

  useEffect(() => {
    heading.current?.focus();
  }, []);

  return (
    <section id={id} className="page-grid tranche" aria-labelledby={headingId}>
      <form className="card form" onSubmit={(event) => event.preventDefault()}>
        <h2 id={headingId} ref={heading} tabIndex={-1}>
          Новый транш
        </h2>
        <Select label="Продукт" value={loanId} placeholder="Выберите продукт" options={PRODUCTS} onChange={setLoanId} />
        <AmountField label="Сумма" value={amountText} onChange={setAmountText} />
      </form>
      <aside>
        <ActionPanel
          context={loanContextOf(loan, heldAmount)}
          placeholder={
            <PanelPlaceholder
              title="Проверка транша"
              text="Выберите продукт и сумму — Alpha Impact покажет новости и позицию банка по ставке, которые касаются этого транша"
              steps={[
                ["Продукт", loan !== undefined],
                ["Сумма", parseAmount(amountText) !== null],
              ]}
            />
          }
        />
      </aside>
    </section>
  );
}
