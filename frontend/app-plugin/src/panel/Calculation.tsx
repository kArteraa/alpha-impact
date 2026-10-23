import type { WhatIfResult } from "../types";
import { Block } from "./Block";
import { CALCULATION_TITLES, formatMoney } from "./labels";

interface CalculationProps {
  result: WhatIfResult;
  compact: boolean;
}

export function Calculation({ result, compact }: CalculationProps) {
  const title = CALCULATION_TITLES[result.kind];
  return (
    <Block title="Расчёт" collapsible={compact} className="insight-block-calc">
      {title && <p className="calc-title">{title}</p>}
      <p className="calc-value">{formatMoney(result.value, result.unit)}</p>
      <p className="calc-formula">{result.formula}</p>
      <ul className="calc-assumptions" aria-label="Допущения">
        {result.assumptions.map((assumption) => (
          <li key={assumption}>{assumption}</li>
        ))}
      </ul>
    </Block>
  );
}
