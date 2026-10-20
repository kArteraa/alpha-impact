import { SIGNIFICANCE_LEVELS, significanceLevel } from "./labels";

export function Significance({ value }: { value: number }) {
  const level = significanceLevel(value);
  return (
    <span
      className="significance"
      role="img"
      aria-label={`Значимость ${level} из ${SIGNIFICANCE_LEVELS}`}
      title={`Значимость ${level} из ${SIGNIFICANCE_LEVELS}`}
    >
      {Array.from({ length: SIGNIFICANCE_LEVELS }, (_, index) => (
        <span key={index} className={index < level ? "dot dot-on" : "dot dot-off"} />
      ))}
    </span>
  );
}
