import { Icon } from "../ui/Icon";

interface PanelPlaceholderProps {
  recipient: boolean;
  amount: boolean;
}

export function PanelPlaceholder({ recipient, amount }: PanelPlaceholderProps) {
  const steps = [
    ["Получатель", recipient],
    ["Сумма", amount],
  ] as const;
  return (
    <div className="card panel-placeholder">
      <h2>Проверка платежа</h2>
      <p className="muted">Выберите получателя и сумму — Alpha Impact покажет новости и позицию банка, которые касаются этого платежа</p>
      <ol className="placeholder-steps">
        {steps.map(([label, done], index) => (
          <li key={label} data-done={done}>
            <span className="placeholder-step-mark" aria-hidden="true">
              {done ? <Icon name="check" size={16} /> : index + 1}
            </span>
            {label}
            <span className="visually-hidden">{done ? " — готово" : " — не заполнено"}</span>
          </li>
        ))}
      </ol>
    </div>
  );
}
