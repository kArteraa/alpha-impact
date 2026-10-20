import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { PaymentPage } from "./PaymentPage";

function fill(beneficiaryId: string, amount: string) {
  fireEvent.change(screen.getByLabelText("Получатель"), { target: { value: beneficiaryId } });
  fireEvent.change(screen.getByLabelText("Сумма, ₽"), { target: { value: amount } });
}

function panel() {
  return document.querySelector(".insight-panel");
}

describe("PaymentPage", () => {
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("shows a hint instead of the panel until the form is filled", () => {
    render(<PaymentPage />);

    expect(screen.getByText(/Выберите получателя и сумму/)).toBeTruthy();
    expect(panel()).toBeNull();
  });

  it("lists the seed counterparties as recipients", () => {
    render(<PaymentPage />);

    const values = Array.from(screen.getByLabelText<HTMLSelectElement>("Получатель").options, (o) => o.value);
    expect(values).toEqual(expect.arrayContaining(["cp_logistics_spb", "cp_stationery"]));
  });

  it("keeps the recipient label stable after a recipient is chosen", () => {
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500000");

    const describedBy = screen.getByLabelText("Получатель").getAttribute("aria-describedby");
    expect(describedBy).toBe(screen.getByText("Грузоперевозки, Санкт-Петербург").id);
  });

  it("shows insight cards for the carrier payment", () => {
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500000");

    expect(panel()?.getAttribute("data-state")).toBe("cards");
    expect(panel()?.getAttribute("data-action-type")).toBe("payment");
  });

  it("stays silent for the stationery supplier", () => {
    render(<PaymentPage />);
    fill("cp_stationery", "20000");

    expect(panel()?.getAttribute("data-state")).toBe("silent");
  });

  it("keeps the panel while the amount is being typed", () => {
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500");
    const shown = panel();

    fireEvent.change(screen.getByLabelText("Сумма, ₽"), { target: { value: "1500," } });

    expect(panel()).toBe(shown);
    expect(panel()?.getAttribute("data-state")).toBe("cards");
    expect(screen.getByRole<HTMLButtonElement>("button", { name: "Продолжить" }).disabled).toBe(true);
  });

  it("follows the recipient while the amount is being typed", () => {
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500");
    fireEvent.change(screen.getByLabelText("Сумма, ₽"), { target: { value: "1500," } });

    fireEvent.change(screen.getByLabelText("Получатель"), { target: { value: "cp_stationery" } });
    expect(panel()?.getAttribute("data-state")).toBe("silent");

    fireEvent.change(screen.getByLabelText("Получатель"), { target: { value: "" } });
    expect(panel()).toBeNull();
  });

  it("hides the panel when the amount is cleared", () => {
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500");

    fireEvent.change(screen.getByLabelText("Сумма, ₽"), { target: { value: "" } });

    expect(panel()).toBeNull();
  });

  it("hands the PaymentContext to the console on submit", () => {
    const info = vi.spyOn(console, "info").mockImplementation(() => {});
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500000");
    fireEvent.change(screen.getByLabelText("Назначение платежа"), { target: { value: "Оплата перевозки" } });

    fireEvent.click(screen.getByRole("button", { name: "Продолжить" }));

    expect(info).toHaveBeenCalledWith("PaymentContext", {
      type: "payment",
      amount: 1500000,
      beneficiary_id: "cp_logistics_spb",
    });
  });
});
