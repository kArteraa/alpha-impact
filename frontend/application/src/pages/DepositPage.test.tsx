import { mockResponses } from "@alpha-impact/plugin";
import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  answer,
  askedContext,
  panelState,
  placeholderSteps,
  renderWithCompany,
  setAmount,
  stubApi,
} from "../testing";
import { DepositPage } from "./DepositPage";

function render() {
  return renderWithCompany(<DepositPage />, { path: "/deposits/new" });
}

function chooseTerm(term: string) {
  fireEvent.click(screen.getByRole("radio", { name: term }));
}

function income() {
  return screen.getByTestId("deposit-income").textContent?.replace(/\s/g, " ");
}

describe("DepositPage", () => {
  let fetchMock: ReturnType<typeof stubApi>;

  beforeEach(() => {
    vi.useFakeTimers();
    fetchMock = stubApi({ "POST /api/interpret": [200, mockResponses.rates] });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("offers the term as a segmented choice", () => {
    render();

    const group = screen.getByRole("radiogroup", { name: "Срок" });
    expect(group.textContent).toBe("3 мес.6 мес.12 мес.");
    expect(screen.getByRole<HTMLInputElement>("radio", { name: "6 мес." }).checked).toBe(true);
  });

  it("recalculates the income next to the form", () => {
    render();
    setAmount("1000000");
    expect(income()).toBe("76 000,00 ₽");

    chooseTerm("3 мес.");

    expect(screen.getByRole<HTMLInputElement>("radio", { name: "3 мес." }).checked).toBe(true);
    expect(income()).toBe("36 250,00 ₽");
    expect(screen.getByText(/14,5% годовых/)).toBeTruthy();
  });

  it("announces the income without reading the chart aloud", () => {
    render();
    setAmount("1000000");

    const live = document.querySelector("[aria-live]");
    expect(live?.contains(screen.getByTestId("deposit-income"))).toBe(true);
    expect(live?.querySelector("table, svg")).toBeNull();
  });

  it("asks for an amount before calculating", () => {
    render();

    expect(screen.getByText("Введите сумму — посчитаю доход за выбранный срок")).toBeTruthy();
  });

  it("shows a hint instead of the panel until the amount is entered", () => {
    render();

    expect(screen.getByRole("heading", { name: "Проверка депозита" })).toBeTruthy();
    expect(placeholderSteps()).toEqual(["false", "true"]);
    expect(panelState()).toBeUndefined();
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("asks /interpret about the deposit with the term in days", async () => {
    render();
    setAmount("50000000");
    await answer();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(askedContext(fetchMock, 0)).toEqual({ type: "deposit", amount: 50000000, term_days: 180 });
  });

  it("asks again when the term changes", async () => {
    render();
    setAmount("50000000");
    await answer();

    chooseTerm("3 мес.");
    await answer();

    expect(fetchMock).toHaveBeenCalledTimes(2);
    expect(askedContext(fetchMock, 1)).toEqual({ type: "deposit", amount: 50000000, term_days: 90 });
  });

  it("shows the bank view on the rate and the calculation in the panel", async () => {
    render();
    setAmount("50000000");
    expect(panelState()).toBe("checking");

    await answer();

    expect(panelState()).toBe("cards");
    expect(document.querySelector(".insight-panel")?.getAttribute("data-action-type")).toBe("deposit");
    expect(screen.getAllByLabelText(/^Банк — источник: /).length).toBeGreaterThan(0);
    expect(screen.getByRole("region", { name: "Расчёт" })).toBeTruthy();
  });

  it("leads the bank source to the page of the report through the API", async () => {
    render();
    setAmount("50000000");
    await answer();

    expect(screen.getByLabelText(/^Банк — источник: /).getAttribute("href")).toBe(
      "/api/reports/ALFA-Macro_Insights-Policy_Rate_11Sep.pdf#page=1",
    );
  });

  it("keeps the panel while the amount is being typed", async () => {
    render();
    setAmount("1500");
    await answer();
    const shown = document.querySelector(".insight-card");

    setAmount("1500,");
    await answer();

    expect(document.querySelector(".insight-card")).toBe(shown);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("explains an amount it cannot accept while the panel keeps the last one", async () => {
    render();
    setAmount("50000000");
    await answer();

    setAmount("5000000O");

    expect(panelState()).toBe("cards");
    expect(screen.getByText("Сумма — положительное число, не больше двух знаков после запятой")).toBeTruthy();
    expect(screen.getByLabelText("Сумма, ₽").getAttribute("aria-invalid")).toBe("true");
  });
});
