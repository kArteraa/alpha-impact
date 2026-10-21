import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { RUB_WHOLE } from "../money";
import { LoansPage } from "./LoansPage";

describe("LoansPage", () => {
  afterEach(cleanup);

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
    expect(stat("Ближайшее погашение")).toContain("Овердрафт");
  });
});
