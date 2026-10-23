import { mockResponses } from "@alpha-impact/plugin";
import { cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RUB_WHOLE } from "../money";
import {
  answer,
  askedContext,
  chooseOption,
  placeholderSteps,
  renderWithCompany,
  setAmount,
  stubApi,
} from "../testing";
import { LoansPage } from "./LoansPage";

function render() {
  return renderWithCompany(<LoansPage />, { path: "/loans" });
}

function trancheButton() {
  return screen.getByRole("button", { name: "Новый транш" });
}

function openTranche() {
  render();
  fireEvent.click(trancheButton());
}

describe("LoansPage", () => {
  let fetchMock: ReturnType<typeof stubApi>;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-10-22T09:00:00+03:00"));
    fetchMock = stubApi({ "POST /api/interpret": [200, mockResponses.rates] });
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("shows the portfolio as a table with a new tranche action", () => {
    render();

    const table = screen.getByRole("table", { name: "Кредитный портфель" });
    expect(table.querySelectorAll("tbody tr").length).toBe(3);
    expect(screen.getByRole("columnheader", { name: "Сумма" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Новый транш" })).toBeTruthy();
  });

  it("sums up the portfolio above the table", () => {
    render();

    const stat = (label: string) => screen.getByText(label).closest(".stat")?.textContent;
    expect(stat("Общая сумма")).toContain(RUB_WHOLE.format(173_400_000));
    expect(stat("Продуктов")).toContain("3");
    expect(stat("Ближайшее погашение")).toContain("31.12.2026");
    expect(stat("Ближайшее погашение")).toContain("Овердрафт · через 70 дней");
  });

  it("shows the structure of the portfolio by product", () => {
    render();

    const legend = screen.getByRole("list", { name: "Структура портфеля" });
    const items = Array.from(legend.querySelectorAll("li"), (item) => item.textContent?.replace(/\s/g, " "));
    expect(items).toEqual([
      "Кредитная линия120 000 000 ₽ · 69 %",
      "Лизинг транспорта38 400 000 ₽ · 22 %",
      "Овердрафт15 000 000 ₽ · 9 %",
    ]);
  });

  it("says a passed repayment is overdue", () => {
    vi.setSystemTime(new Date("2027-01-21T09:00:00+03:00"));
    render();

    expect(screen.getByText("Ближайшее погашение").closest(".stat")?.textContent).toContain(
      "Овердрафт · просрочено на 21 день",
    );
    const badge = document.querySelector("tbody tr td:last-child .badge");
    expect(badge?.textContent).toBe("просрочено на 21 день");
    expect(badge?.className).toBe("badge badge-danger");
  });

  it("says a repayment due today is today in the table too", () => {
    vi.setSystemTime(new Date("2026-12-31T09:00:00+03:00"));
    render();

    expect(document.querySelector("tbody tr td:last-child")?.textContent).toBe("сегодня");
  });

  it("orders the loans by maturity with the days left", () => {
    render();

    const rows = Array.from(document.querySelectorAll("tbody tr"), (row) => [
      row.querySelector("td")?.textContent,
      row.querySelector("td:last-child")?.textContent,
    ]);
    expect(rows).toEqual([
      ["Овердрафт", "70 дней"],
      ["Кредитная линия", "251 день"],
      ["Лизинг транспорта", "526 дней"],
    ]);
  });

  it("marks the portfolio as demo data", () => {
    render();

    const head = screen.getByRole("heading", { name: "Кредитный портфель" }).closest(".table-head");
    expect(within(head as HTMLElement).getByText("демо-данные")).toBeTruthy();
  });

  it("opens the tranche form under the portfolio and moves focus to it", () => {
    render();
    expect(trancheButton().getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("heading", { name: "Новый транш" })).toBeNull();

    fireEvent.click(trancheButton());

    expect(trancheButton().getAttribute("aria-expanded")).toBe("true");
    const heading = screen.getByRole("heading", { name: "Новый транш" });
    expect(document.activeElement).toBe(heading);
    expect(trancheButton().getAttribute("aria-controls")).toBe(heading.closest("section")?.id);
    const table = screen.getByRole("table", { name: "Кредитный портфель" });
    expect(table.compareDocumentPosition(heading) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("closes the tranche form on a second click", () => {
    openTranche();

    fireEvent.click(trancheButton());

    expect(trancheButton().getAttribute("aria-expanded")).toBe("false");
    expect(screen.queryByRole("heading", { name: "Новый транш" })).toBeNull();
  });

  it("offers the products of the portfolio with their rates", () => {
    openTranche();
    expect(screen.getByRole("combobox", { name: "Продукт" }).textContent).toContain("Выберите продукт");

    fireEvent.click(screen.getByRole("combobox", { name: "Продукт" }));

    const options = screen.getAllByRole("option").map((option) => option.textContent?.replace(/\s/g, " "));
    expect(options).toEqual([
      "Кредитная линияключевая + 2,5% · 120 000 000 ₽",
      "Лизинг транспорта17,9% фикс. · 38 400 000 ₽",
      "Овердрафтключевая + 3% · 15 000 000 ₽",
    ]);
  });

  it("shows a hint instead of the panel until the product and the amount are chosen", () => {
    openTranche();

    expect(screen.getByRole("heading", { name: "Проверка транша" })).toBeTruthy();
    expect(placeholderSteps()).toEqual(["false", "false"]);

    chooseOption("Продукт", /Кредитная линия/);

    expect(placeholderSteps()).toEqual(["true", "false"]);
    expect(document.querySelector(".insight-panel")).toBeNull();
  });

  it("asks /interpret about a tranche of the credit line at a floating rate", async () => {
    openTranche();
    chooseOption("Продукт", /Кредитная линия/);
    setAmount("50000000");
    await answer();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(askedContext(fetchMock, 0)).toEqual({
      type: "loan",
      product: "loan",
      amount: 50000000,
      rate_type: "floating",
    });
    expect(document.querySelector(".insight-panel")?.getAttribute("data-action-type")).toBe("loan");
    expect(screen.getAllByLabelText(/^Банк — источник: /).length).toBeGreaterThan(0);
    expect(screen.getByRole("region", { name: "Расчёт" })).toBeTruthy();
  });

  it("explains a tranche amount it cannot accept", () => {
    openTranche();

    setAmount("1500.555");

    expect(screen.getByText("Сумма — положительное число, не больше двух знаков после запятой")).toBeTruthy();
    expect(screen.getByLabelText("Сумма, ₽").getAttribute("aria-invalid")).toBe("true");
  });
});
