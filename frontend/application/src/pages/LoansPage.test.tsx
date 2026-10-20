import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
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
});
