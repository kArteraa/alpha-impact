import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockResponses } from "../mocks";
import type { InterpretResponse, WhatIfResult } from "../types";
import { InsightPanel } from "./InsightPanel";

const context = { type: "deposit", amount: 50_000_000, term_days: 360 } as const;

const RATE_BURDEN: WhatIfResult = {
  kind: "rate_burden",
  value: -290_000,
  unit: "RUB",
  formula: "50 000 000 ₽ × (13,42% − 14%) × 12/12 мес. = −290 000 ₽",
  assumptions: ["ставка меняется сразу и держится весь срок"],
};

function withCalculation(calculation: WhatIfResult): InterpretResponse {
  const card = mockResponses.rates.cards[0];
  return { ...mockResponses.rates, cards: [{ ...card, calculation }] };
}

function calculation() {
  return screen.getByRole("region", { name: "Расчёт" });
}

function spaced(text: string | null | undefined) {
  return text?.replace(/\s/g, " ");
}

describe("InsightPanel calculation", () => {
  afterEach(cleanup);

  it("shows what was calculated, the signed sum, the formula and every assumption", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.rates} />);

    const block = calculation();
    const result = mockResponses.rates.cards[0].calculation;
    expect(within(block).getByText("Выгода фиксации ставки против помесячного переразмещения")).toBeTruthy();
    expect(spaced(block.querySelector(".calc-value")?.textContent)).toBe("+286 027,40 ₽");
    expect(within(block).getByText(result?.formula ?? "")).toBeTruthy();
    const assumptions = within(block).getByRole("list", { name: "Допущения" });
    expect(Array.from(assumptions.querySelectorAll("li"), (item) => item.textContent)).toEqual(result?.assumptions);
  });

  it("shows a whole saving on the rate without kopecks", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={withCalculation(RATE_BURDEN)} />);

    const block = calculation();
    expect(within(block).getByText("Изменение процентных расходов при плавающей ставке")).toBeTruthy();
    expect(spaced(block.querySelector(".calc-value")?.textContent)).toMatch(/^[−-]290 000 ₽$/);
  });

  it.each(["fx_exposure", "constructor"])("shows no caption for a calculation it does not know: %s", (kind) => {
    render(<InsightPanel actionContext={context} role="cfo" response={withCalculation({ ...RATE_BURDEN, kind })} />);

    expect(calculation().querySelector(".calc-title")).toBeNull();
  });

  it("shows a value in a unit that is not a currency next to its unit", () => {
    render(
      <InsightPanel
        actionContext={context}
        role="cfo"
        response={withCalculation({ ...RATE_BURDEN, value: 1.5, unit: "%" })}
      />,
    );

    expect(spaced(calculation().querySelector(".calc-value")?.textContent)).toBe("+1,50 %");
  });

  it("lists a repeated assumption every time it comes", () => {
    const error = vi.spyOn(console, "error").mockImplementation(() => {});
    const repeated = { ...RATE_BURDEN, assumptions: ["без налогов", "без налогов"] };
    render(<InsightPanel actionContext={context} role="cfo" response={withCalculation(repeated)} />);

    const assumptions = within(calculation()).getByRole("list", { name: "Допущения" });
    expect(assumptions.querySelectorAll("li").length).toBe(2);
    expect(error).not.toHaveBeenCalled();
    error.mockRestore();
  });

  it("has no calculation block when the card carries none", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    expect(screen.queryByRole("region", { name: "Расчёт" })).toBeNull();
  });

  it("folds the calculation behind its heading when compact", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.rates} compact />);

    const toggle = screen.getByRole("button", { name: "Расчёт" });
    expect(toggle.getAttribute("aria-expanded")).toBe("false");
    expect(document.querySelector(".calc-value")).toBeNull();

    fireEvent.click(toggle);

    expect(spaced(document.querySelector(".calc-value")?.textContent)).toBe("+286 027,40 ₽");
  });
});
