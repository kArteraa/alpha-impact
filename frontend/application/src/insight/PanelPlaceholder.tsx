import { Icon } from "../ui/Icon";

interface PanelPlaceholderProps {
  title: string;
  text: string;
  steps: readonly (readonly [label: string, done: boolean])[];
}

export function PanelPlaceholder({ title, text, steps }: PanelPlaceholderProps) {
  return (
    <div className="card panel-placeholder">
      <h2>{title}</h2>
      <p className="muted">{text}</p>
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
