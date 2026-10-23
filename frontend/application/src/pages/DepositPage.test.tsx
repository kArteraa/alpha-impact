import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { DepositPage } from "./DepositPage";

function income() {
  return screen.getByTestId("deposit-income").textContent?.replace(/\s/g, " ");
}

describe("DepositPage", () => {
  afterEach(cleanup);

  it("offers the term as a segmented choice", () => {
    render(<DepositPage />);

    const group = screen.getByRole("radiogroup", { name: "Срок" });
    expect(group.textContent).toBe("3 мес.6 мес.12 мес.");
    expect(screen.getByRole<HTMLInputElement>("radio", { name: "6 мес." }).checked).toBe(true);
  });

  it("recalculates the income next to the form", () => {
    render(<DepositPage />);
    fireEvent.change(screen.getByLabelText("Сумма, ₽"), { target: { value: "1000000" } });
    expect(income()).toBe("76 000,00 ₽");

    fireEvent.click(screen.getByRole("radio", { name: "3 мес." }));

    expect(screen.getByRole<HTMLInputElement>("radio", { name: "3 мес." }).checked).toBe(true);
    expect(income()).toBe("36 250,00 ₽");
    expect(screen.getByText(/14,5% годовых/)).toBeTruthy();
  });

  it("announces the income without reading the chart aloud", () => {
    render(<DepositPage />);
    fireEvent.change(screen.getByLabelText("Сумма, ₽"), { target: { value: "1000000" } });

    const live = document.querySelector("[aria-live]");
    expect(live?.contains(screen.getByTestId("deposit-income"))).toBe(true);
    expect(live?.querySelector("table, svg")).toBeNull();
  });

  it("asks for an amount before calculating", () => {
    render(<DepositPage />);

    expect(screen.getByText("Введите сумму — посчитаю доход за выбранный срок")).toBeTruthy();
  });
});
