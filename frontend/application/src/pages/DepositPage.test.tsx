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

    const terms = screen.getAllByRole("radio").map((option) => option.textContent);
    expect(terms).toEqual(["3 мес.", "6 мес.", "12 мес."]);
    expect(screen.getByRole("radio", { name: "6 мес." }).getAttribute("aria-checked")).toBe("true");
  });

  it("recalculates the income next to the form", () => {
    render(<DepositPage />);
    fireEvent.change(screen.getByLabelText("Сумма, ₽"), { target: { value: "1000000" } });
    expect(income()).toBe("76 000,00 ₽");

    fireEvent.click(screen.getByRole("radio", { name: "3 мес." }));

    expect(screen.getByRole("radio", { name: "3 мес." }).getAttribute("aria-checked")).toBe("true");
    expect(income()).toBe("36 250,00 ₽");
    expect(screen.getByText(/14,5% годовых/)).toBeTruthy();
  });

  it("asks for an amount before calculating", () => {
    render(<DepositPage />);

    expect(screen.getByText("Введите сумму — посчитаю доход за выбранный срок")).toBeTruthy();
  });
});
