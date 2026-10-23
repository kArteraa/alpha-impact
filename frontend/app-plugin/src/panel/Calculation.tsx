import type { WhatIfResult } from "../types";
import { Block } from "./Block";
import { CALCULATION_TITLES, formatValue } from "./labels";

interface CalculationProps {
  result: WhatIfResult;
  compact: boolean;
}

export function Calculation({ result, compact }: CalculationProps) {
  const title = CALCULATION_TITLES.get(result.kind);
  return (
    <Block title="Расчёт" collapsible={compact} className="insight-block-calc">
      {title && <p className="calc-title">{title}</p>}
      <p className="calc-value">{formatValue(result.value, result.unit)}</p>
      <p className="calc-formula">{result.formula}</p>
      <ul className="calc-assumptions" aria-label="Допущения">
        {result.assumptions.map((assumption, index) => (
          <li key={index}>{assumption}</li>
        ))}
      </ul>
    </Block>
  );
}
