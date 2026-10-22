import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { RUB_WHOLE } from "../money";
import { LoansPage } from "./LoansPage";

describe("LoansPage", () => {
  beforeEach(() => {
    vi.useFakeTimers({ toFake: ["Date"] });
    vi.setSystemTime(new Date("2026-10-22T09:00:00+03:00"));
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
  });

  it("shows the portfolio as a table with a new tranche action", () => {
    render(<LoansPage />);

    const table = screen.getByRole("table", { name: "Кредитный портфель" });
    expect(table.querySelectorAll("tbody tr").length).toBe(3);
    expect(screen.getByRole("columnheader", { name: "Сумма" })).toBeTruthy();
    expect(screen.getByRole("button", { name: "Новый транш" })).toBeTruthy();
  });

  it("sums up the portfolio above the table", () => {
    render(<LoansPage />);

    const stat = (label: string) => screen.getByText(label).closest(".stat")?.textContent;
    expect(stat("Общая сумма")).toContain(RUB_WHOLE.format(173_400_000));
    expect(stat("Продуктов")).toContain("3");
    expect(stat("Ближайшее погашение")).toContain("31.12.2026");
    expect(stat("Ближайшее погашение")).toContain("Овердрафт · через 70 дней");
  });

  it("shows the structure of the portfolio by product", () => {
    render(<LoansPage />);

    const legend = screen.getByRole("list", { name: "Структура портфеля" });
    const items = Array.from(legend.querySelectorAll("li"), (item) => item.textContent?.replace(/\s/g, " "));
    expect(items).toEqual([
      "Кредитная линия120 000 000 ₽ · 69 %",
      "Лизинг транспорта38 400 000 ₽ · 22 %",
      "Овердрафт15 000 000 ₽ · 9 %",
    ]);
  });

  it("orders the loans by maturity with the days left", () => {
    render(<LoansPage />);

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
});
