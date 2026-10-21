import { RUB } from "../money";

export function Amount({ value, className, testId }: { value: number; className?: string; testId?: string }) {
  const text = RUB.format(value);
  const comma = text.lastIndexOf(",");
  return (
    <strong className={className} data-testid={testId}>
      {text.slice(0, comma)}
      <span className="amount-tail">{text.slice(comma)}</span>
    </strong>
  );
}
