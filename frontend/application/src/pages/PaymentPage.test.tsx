import { INTERPRET_DELAY_MS } from "@alpha-impact/plugin";
import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { PaymentPage } from "./PaymentPage";

function amountField() {
  return screen.getByLabelText<HTMLInputElement>("Сумма, ₽");
}

function setAmount(amount: string) {
  fireEvent.change(amountField(), { target: { value: amount } });
}

function setRecipient(beneficiaryId: string) {
  fireEvent.change(screen.getByLabelText("Получатель"), { target: { value: beneficiaryId } });
}

function fill(beneficiaryId: string, amount: string) {
  setRecipient(beneficiaryId);
  setAmount(amount);
}

async function answer() {
  act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS));
  await act(async () => {
    await Promise.resolve();
  });
}

function panelState() {
  return document.querySelector(".insight-panel")?.getAttribute("data-state");
}

describe("PaymentPage", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it("shows a hint instead of the panel until the form is filled", () => {
    render(<PaymentPage />);

    expect(screen.getByText(/Выберите получателя и сумму/)).toBeTruthy();
    expect(panelState()).toBeUndefined();
  });

  it("lists the seed counterparties as recipients", () => {
    render(<PaymentPage />);

    const values = Array.from(screen.getByLabelText<HTMLSelectElement>("Получатель").options, (o) => o.value);
    expect(values).toEqual(expect.arrayContaining(["cp_logistics_spb", "cp_stationery"]));
  });

  it("describes the chosen recipient for assistive technology", () => {
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500000");

    const describedBy = screen.getByLabelText("Получатель").getAttribute("aria-describedby");
    expect(describedBy).toBe(screen.getByText("Грузоперевозки, Санкт-Петербург").id);
  });

  it("checks first and shows the carrier insight after the delay", async () => {
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500000");

    expect(panelState()).toBe("checking");
    await answer();

    expect(panelState()).toBe("cards");
    expect(document.querySelector(".insight-panel")?.getAttribute("data-action-type")).toBe("payment");
  });

  it("stays silent for the stationery supplier", async () => {
    render(<PaymentPage />);
    fill("cp_stationery", "20000");
    await answer();

    expect(panelState()).toBe("silent");
  });

  it("keeps the panel while the amount is being typed", async () => {
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500");
    await answer();
    const shown = document.querySelector(".insight-card");

    setAmount("1500,");

    expect(document.querySelector(".insight-card")).toBe(shown);
    expect(screen.getByRole<HTMLButtonElement>("button", { name: "Отправить" }).disabled).toBe(true);
  });

  it("follows the recipient while the amount is being typed", async () => {
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500");
    await answer();
    setAmount("1500,");

    setRecipient("cp_stationery");
    await answer();
    expect(panelState()).toBe("silent");

    setRecipient("");
    expect(panelState()).toBeUndefined();
  });

  it("hides the panel when the amount is cleared", async () => {
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500");
    await answer();

    setAmount("");

    expect(panelState()).toBeUndefined();
  });

  it("formats the amount in rubles when the field loses focus", () => {
    render(<PaymentPage />);
    setAmount("1500000");

    fireEvent.blur(amountField());

    expect(amountField().value.replace(/\s/g, " ")).toBe("1 500 000");
  });

  it("explains an amount it cannot accept", () => {
    render(<PaymentPage />);
    setAmount("1500.555");

    expect(screen.getByText("Сумма — число, не больше двух знаков после запятой")).toBeTruthy();
    expect(amountField().getAttribute("aria-invalid")).toBe("true");
  });

  it("has a single primary action", () => {
    render(<PaymentPage />);

    expect(document.querySelectorAll(".button").length).toBe(1);
    expect(screen.getByRole("button", { name: "Отправить" }).className).toBe("button");
  });

  it("hands the PaymentContext to the console on submit", () => {
    const info = vi.spyOn(console, "info").mockImplementation(() => {});
    render(<PaymentPage />);
    fill("cp_logistics_spb", "1500000");
    fireEvent.change(screen.getByLabelText("Назначение платежа"), { target: { value: "Оплата перевозки" } });

    fireEvent.click(screen.getByRole("button", { name: "Отправить" }));

    expect(info).toHaveBeenCalledWith("PaymentContext", {
      type: "payment",
      amount: 1500000,
      beneficiary_id: "cp_logistics_spb",
    });
  });
});
