import { mockResponses } from "@alpha-impact/plugin";
import { act, cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { COUNTERPARTIES } from "../data/counterparties";
import {
  TEST_CLIENT,
  TEST_USER,
  answer,
  chooseOption,
  panelState,
  placeholderSteps,
  renderWithCompany,
  setAmount,
  stubApi,
} from "../testing";
import { PaymentPage } from "./PaymentPage";

const [CARRIER, STATIONERY] = COUNTERPARTIES.map((counterparty) => counterparty.id);

function stubInterpret() {
  return stubApi({
    "POST /api/interpret": (init) => {
      const body = JSON.parse(String(init?.body));
      return [200, body.action_context.beneficiary_id === CARRIER ? mockResponses.cards : mockResponses.silent];
    },
  });
}

function render(node = <PaymentPage />) {
  return renderWithCompany(node, { path: "/payments/new" });
}

function amountField() {
  return screen.getByLabelText<HTMLInputElement>("Сумма, ₽");
}

function setRecipient(beneficiaryId: string) {
  const name = COUNTERPARTIES.find((counterparty) => counterparty.id === beneficiaryId)?.name ?? "";
  chooseOption("Получатель", new RegExp(name));
}

function fill(beneficiaryId: string, amount: string) {
  setRecipient(beneficiaryId);
  setAmount(amount);
}

describe("PaymentPage", () => {
  let fetchMock: ReturnType<typeof stubInterpret>;

  beforeEach(() => {
    vi.useFakeTimers();
    fetchMock = stubInterpret();
  });

  afterEach(() => {
    cleanup();
    vi.useRealTimers();
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("shows a hint instead of the panel until the form is filled", () => {
    render();

    expect(screen.getByText(/Выберите получателя и сумму/)).toBeTruthy();
    expect(panelState()).toBeUndefined();
  });

  it("lists real counterparties of the wholesaler as recipients", () => {
    render();
    expect(screen.getByRole("combobox", { name: "Получатель" }).textContent).toContain("Выберите контрагента");

    fireEvent.click(screen.getByRole("combobox", { name: "Получатель" }));

    const options = screen.getAllByRole("option").map((option) => option.textContent);
    expect(options).toEqual([
      "ООО «Северо-Западная логистика»Грузоперевозки, Санкт-Петербург",
      "ООО «Канцмир»Канцелярские товары, Москва",
    ]);
    expect(COUNTERPARTIES.map((counterparty) => counterparty.id)).toEqual(["U_96105", STATIONERY]);
    expect(STATIONERY).toMatch(/^U_\d+$/);
  });

  it("does not mark an amount it cannot accept as done", () => {
    render();
    setAmount("1000");
    setAmount("1000abc");

    expect(placeholderSteps()).toEqual(["false", "false"]);
  });

  it("marks the steps of the form done in the placeholder", () => {
    render();
    setRecipient(CARRIER);

    expect(placeholderSteps()).toEqual(["true", "false"]);
  });

  it("asks /interpret for the signed-in user, company and role", async () => {
    render();
    fill(CARRIER, "1500000");
    await answer();

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/interpret");
    expect(JSON.parse(String(init?.body))).toEqual({
      user_id: TEST_USER,
      client_id: TEST_CLIENT,
      role: "cfo",
      action_context: { type: "payment", amount: 1500000, beneficiary_id: CARRIER },
    });
  });

  it("sends feedback on the card", async () => {
    fetchMock = stubApi({ "POST /api/interpret": [200, mockResponses.cards], "POST /api/feedback": [204, null] });
    render();
    fill(CARRIER, "1500000");
    await answer();

    fireEvent.click(screen.getByRole("button", { name: "Полезно" }));
    await act(async () => {});

    const [url, init] = fetchMock.mock.calls[1];
    expect(url).toBe("/api/feedback");
    expect(JSON.parse(String(init?.body))).toEqual({ card_id: "card-mock-1", useful: true });
    expect(screen.getByRole("button", { name: "Полезно" }).getAttribute("aria-pressed")).toBe("true");
  });

  it("shows the panel for the role of the user", async () => {
    renderWithCompany(<PaymentPage />, { path: "/payments/new", role: "treasurer" });
    fill(CARRIER, "1500000");

    expect(document.querySelector(".insight-panel")?.getAttribute("data-role")).toBe("treasurer");
  });

  it("offers a retry when the request fails", async () => {
    stubApi({});
    render();
    fill(CARRIER, "1500000");
    await answer();

    expect(panelState()).toBe("failed");
  });

  it("describes the chosen recipient for assistive technology", () => {
    render();
    fill(CARRIER, "1500000");

    const describedBy = screen.getByRole("combobox", { name: "Получатель" }).getAttribute("aria-describedby");
    expect(describedBy).toBe(screen.getByText("Грузоперевозки, Санкт-Петербург").id);
  });

  it("checks first and shows the carrier insight after the delay", async () => {
    render();
    fill(CARRIER, "1500000");

    expect(panelState()).toBe("checking");
    await answer();

    expect(panelState()).toBe("cards");
    expect(document.querySelector(".insight-panel")?.getAttribute("data-action-type")).toBe("payment");
  });

  it("stays silent for the stationery supplier", async () => {
    render();
    fill(STATIONERY, "20000");
    await answer();

    expect(panelState()).toBe("silent");
  });

  it("keeps the panel while the amount is being typed", async () => {
    render();
    fill(CARRIER, "1500");
    await answer();
    const shown = document.querySelector(".insight-card");

    setAmount("1500,");

    expect(document.querySelector(".insight-card")).toBe(shown);
    expect(screen.getByRole<HTMLButtonElement>("button", { name: "Отправить" }).disabled).toBe(true);
  });

  it("follows the recipient while the amount is being typed", async () => {
    render();
    fill(CARRIER, "1500");
    await answer();
    setAmount("1500,");

    setRecipient(STATIONERY);
    await answer();
    expect(panelState()).toBe("silent");
  });

  it("hides the panel when the amount is cleared", async () => {
    render();
    fill(CARRIER, "1500");
    await answer();

    setAmount("");

    expect(panelState()).toBeUndefined();
  });

  it("formats the amount in rubles when the field loses focus", () => {
    render();
    setAmount("1500000");

    fireEvent.blur(amountField());

    expect(amountField().value.replace(/\s/g, " ")).toBe("1 500 000");
  });

  it.each(["1500.555", "0"])("explains an amount it cannot accept: %s", (amount) => {
    render();
    setAmount(amount);

    expect(screen.getByText("Сумма — положительное число, не больше двух знаков после запятой")).toBeTruthy();
    expect(amountField().getAttribute("aria-invalid")).toBe("true");
  });

  it("has a single primary action", () => {
    render();

    expect(document.querySelectorAll(".button").length).toBe(1);
    expect(screen.getByRole("button", { name: "Отправить" }).className).toBe("button");
  });

  it("hands the PaymentContext to the console on submit", () => {
    const info = vi.spyOn(console, "info").mockImplementation(() => {});
    render();
    fill(CARRIER, "1500000");
    fireEvent.change(screen.getByLabelText("Назначение платежа"), { target: { value: "Оплата перевозки" } });

    fireEvent.click(screen.getByRole("button", { name: "Отправить" }));

    expect(info).toHaveBeenCalledWith("PaymentContext", {
      type: "payment",
      amount: 1500000,
      beneficiary_id: CARRIER,
    });
  });
});
