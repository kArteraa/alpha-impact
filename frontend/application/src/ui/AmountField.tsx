import { useId } from "react";
import { formatRub } from "../money";

interface AmountFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: string | null;
}

export function AmountField({ label, value, onChange, error = null }: AmountFieldProps) {
  const hintId = useId();
  return (
    <label className="field amount-field">
      <span className="muted">{label}</span>
      <input
        aria-label={`${label}, ₽`}
        inputMode="decimal"
        placeholder="0"
        value={value}
        aria-invalid={error !== null}
        aria-describedby={error === null ? undefined : hintId}
        onChange={(event) => onChange(event.target.value)}
        onBlur={() => onChange(formatRub(value))}
      />
      <span className="amount-suffix" aria-hidden="true">
        ₽
      </span>
      {error !== null && (
        <small id={hintId} className="field-hint">
          {error}
        </small>
      )}
    </label>
  );
}
