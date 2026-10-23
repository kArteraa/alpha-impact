import { cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { mockResponses } from "../mocks";
import { InsightPanel } from "./InsightPanel";

const context = { type: "payment", amount: 1500000 } as const;

function state() {
  return document.querySelector(".insight-panel")?.getAttribute("data-state");
}

function blockTitles() {
  return Array.from(document.querySelectorAll(".insight-card h4"), (heading) => heading.textContent);
}

describe("InsightPanel states", () => {
  afterEach(cleanup);

  it("shows a skeleton while checking", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.checking} />);

    expect(state()).toBe("checking");
    expect(document.querySelector(".insight-panel")?.getAttribute("aria-busy")).toBe("true");
    expect(document.querySelectorAll(".insight-skeleton").length).toBe(3);
    expect(screen.getByText("Смотрю новости и позицию банка по этому действию")).toBeTruthy();
  });

  it("shows calm silence with its reason", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.silent} />);

    expect(state()).toBe("silent");
    expect(screen.getByRole("status").textContent).toContain("Ничего важного по этому действию");
    expect(screen.getByText(mockResponses.silent.silent_reason)).toBeTruthy();
  });

  it("admits a failure and offers to retry", () => {
    const onRetry = vi.fn();
    render(<InsightPanel actionContext={context} role="cfo" failed onRetry={onRetry} />);

    expect(state()).toBe("failed");
    expect(screen.getByText("Не успел разобраться с этим действием")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Попробовать ещё раз" }));
    expect(onRetry).toHaveBeenCalledTimes(1);
  });

  it("names the wait and the failure in the host's words", () => {
    render(<InsightPanel actionContext={context} role="cfo" pendingNote="Размечаю новость" failedNote="Не успел" />);
    expect(screen.getByText("Размечаю новость")).toBeTruthy();
    cleanup();

    render(<InsightPanel actionContext={context} role="cfo" failed pendingNote="Размечаю новость" failedNote="Не успел" />);
    expect(screen.getByText("Не успел")).toBeTruthy();
  });

  it("keeps the card and shows progress while a new answer is pending", () => {
    const { rerender } = render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);
    const shown = document.querySelector(".insight-card");

    rerender(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} pending />);

    expect(document.querySelector(".insight-card")).toBe(shown);
    expect(screen.getByRole("progressbar")).toBeTruthy();
  });
  it("treats an answer without cards as silence", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={{ silent: false, cards: [] }} />);

    expect(state()).toBe("silent");
    expect(screen.getByRole("status").textContent).toContain("Ничего важного по этому действию");
  });

  it("shows progress over silence too", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.silent} pending />);

    expect(state()).toBe("silent");
    expect(screen.getByRole("progressbar")).toBeTruthy();
  });
});

describe("InsightPanel card", () => {
  afterEach(cleanup);

  it("orders the blocks from meaning to evidence", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    expect(screen.getByRole("heading", { level: 3 }).textContent).toBe("Логистика в убытке: платёж перевозчику");
    expect(blockTitles()).toEqual([
      "Почему это важно для вас",
      "Что произошло",
      "Последствия",
      "Что можно сделать",
      "Как это оценивает банк",
      "На чём основан вывод",
    ]);
  });

  it("places the calculation between the bank view and the evidence", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.rates} />);

    expect(blockTitles()).toEqual([
      "Почему это важно для вас",
      "Что произошло",
      "Последствия",
      "Что можно сделать",
      "Как это оценивает банк",
      "Расчёт",
      "На чём основан вывод",
    ]);
  });

  it("shows significance as dots, not a number", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    const dots = screen.getByLabelText("Значимость 3 из 3");
    expect(dots.querySelectorAll(".insight-dot-on").length).toBe(3);
  });

  it("marks every claim with a labelled badge that leads to its source", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);
    fireEvent.click(screen.getByRole("button", { name: "Что произошло" }));

    expect(screen.getAllByLabelText(/^Факт — источник: /).length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText(/^Банк — источник: /).length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText(/^AI — источник: /).length).toBeGreaterThan(0);
    const newsBadge = screen.getByLabelText("Факт — источник: Склады маркетплейсов и перевозчики ушли в убыток");
    expect(newsBadge.getAttribute("href")).toBe("https://example.com/news/logistics");
    expect(screen.getByRole("img", { name: "Банк — источник: Обзор отраслей Альфа-Банка, стр. 4" })).toBeTruthy();
  });

  it("never turns a non-http source url into a link", () => {
    const card = mockResponses.cards.cards[0];
    const unsafe = { ...card.why_for_you[0].source_ref, url: "javascript:alert(1)", title: "Подозрительный источник" };
    const response = { ...mockResponses.cards, cards: [{ ...card, why_for_you: [{ ...card.why_for_you[0], source_ref: unsafe }] }] };
    render(<InsightPanel actionContext={context} role="cfo" response={response} />);

    const badge = screen.getByLabelText("Факт — источник: Подозрительный источник");
    expect(badge.tagName).toBe("SPAN");
    expect(badge.getAttribute("href")).toBeNull();
  });

  it("leads a bank source to its report page through the host gateway", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.rates} apiBase="/api" />);

    const basis = screen.getByRole("region", { name: "На чём основан вывод" });
    const page = within(basis).getByRole("link", { name: "ALFA-Macro_Insights-Policy_Rate_11Sep.pdf, стр. 2" });
    expect(page.getAttribute("href")).toBe("/api/reports/ALFA-Macro_Insights-Policy_Rate_11Sep.pdf#page=2");
    expect(page.getAttribute("target")).toBe("_blank");
    const bank = screen.getByRole("region", { name: "Как это оценивает банк" });
    expect(within(bank).getByLabelText(/^Банк — источник: /).getAttribute("href")).toBe(
      "/api/reports/ALFA-Macro_Insights-Policy_Rate_11Sep.pdf#page=1",
    );
  });

  it("keeps a report source as text when the host has no gateway", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.rates} />);

    const basis = screen.getByRole("region", { name: "На чём основан вывод" });
    expect(within(basis).queryByRole("link")).toBeNull();
    expect(within(basis).getByText("ALFA-Macro_Insights-Policy_Rate_11Sep.pdf, стр. 2")).toBeTruthy();
  });

  it.each([
    ["a protocol-relative url of a report", "house_view", "//evil.example/report.pdf"],
    ["a backslash url of a report", "house_view", "/\\evil.example/report.pdf"],
    ["a relative path of a news item", "news", "/news/123"],
  ] as const)("never treats %s as a gateway path", (_, kind, url) => {
    const card = mockResponses.rates.cards[0];
    const other = { ...card.basis[0], kind, url, title: "Чужой путь" };
    const response = { ...mockResponses.rates, cards: [{ ...card, basis: [other] }] };
    render(<InsightPanel actionContext={context} role="cfo" response={response} apiBase="/api" />);

    const basis = screen.getByRole("region", { name: "На чём основан вывод" });
    expect(within(basis).queryByRole("link")).toBeNull();
    expect(within(basis).getByText("Чужой путь")).toBeTruthy();
  });

  it("highlights company traits as chips in the why block", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    const why = screen.getByRole("region", { name: "Почему это важно для вас" });
    expect(within(why).getByText("43% платежей — логистика").className).toContain("chip");
    expect(within(why).getByText("лизинг").className).toContain("chip");
  });

  it("collapses what happened behind a heading button and dates the bank view", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    const toggles = document.querySelectorAll(".insight-card [aria-expanded]");
    expect(toggles.length).toBe(1);
    const whatHappened = screen.getByRole("button", { name: "Что произошло" });
    expect(whatHappened.getAttribute("aria-expanded")).toBe("false");
    expect(screen.getByRole("heading", { level: 4, name: "Что произошло" })).toBeTruthy();
    expect(screen.queryByText("Логистика и складской бизнес показали убыток по итогам квартала")).toBeNull();

    fireEvent.click(whatHappened);

    expect(whatHappened.getAttribute("aria-expanded")).toBe("true");
    expect(screen.getByText("Логистика и складской бизнес показали убыток по итогам квартала")).toBeTruthy();
    const bank = screen.getByRole("region", { name: "Как это оценивает банк" });
    expect(within(bank).getByText(/07\.09\.2026/)).toBeTruthy();
  });

  it("skips a report date it cannot read", () => {
    const card = mockResponses.cards.cards[0];
    const report = { ...card.bank_view[0].source_ref, published_at: "не дата" };
    const response = { ...mockResponses.cards, cards: [{ ...card, bank_view: [{ ...card.bank_view[0], source_ref: report }] }] };
    render(<InsightPanel actionContext={context} role="cfo" response={response} />);

    const bank = screen.getByRole("region", { name: "Как это оценивает банк" });
    expect(within(bank).queryByText(/Отчёт от/)).toBeNull();
    expect(within(bank).getByText("Обзор отраслей Альфа-Банка, стр. 4")).toBeTruthy();
  });

  it("names the type of every source", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    const basis = screen.getByRole("region", { name: "На чём основан вывод" });
    for (const kind of ["новость", "отчёт банка", "данные компании", "расчёт"]) {
      expect(within(basis).getAllByLabelText(kind).length).toBeGreaterThan(0);
    }
  });

  it("offers the product as a quiet separate card", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    const offer = screen.getByRole("region", { name: "Продукт банка" });
    expect(within(offer).getByText("Аккредитив")).toBeTruthy();
    expect(within(offer).getByRole("button", { name: "Узнать подробнее" }).className).toContain("button-secondary");
  });

  it("links the trace and asks a follow-up", () => {
    const onFollowup = vi.fn();
    render(
      <InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} onFollowup={onFollowup} />,
    );

    expect(screen.getByText("Как получен вывод").getAttribute("href")).toBe("/trace/trace-mock-1");
    fireEvent.click(screen.getByRole("button", { name: "Задать вопрос" }));
    expect(onFollowup).toHaveBeenCalledWith("card-mock-1");
  });

  it("hides the follow-up button without a handler", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    expect(screen.queryByRole("button", { name: "Задать вопрос" })).toBeNull();
  });

  it("sends feedback and marks it once it is saved", async () => {
    const onFeedback = vi.fn(() => Promise.resolve());
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} onFeedback={onFeedback} />);
    const useful = screen.getByRole("button", { name: "Полезно" });
    const useless = screen.getByRole("button", { name: "Не полезно" });

    fireEvent.click(useful);

    expect(onFeedback).toHaveBeenCalledWith("card-mock-1", true);
    expect(useful.hasAttribute("disabled")).toBe(true);
    await waitFor(() => expect(useful.getAttribute("aria-pressed")).toBe("true"));
    expect(useless.getAttribute("aria-pressed")).toBe("false");

    fireEvent.click(useful);
    expect(onFeedback).toHaveBeenCalledTimes(1);

    fireEvent.click(useless);

    expect(onFeedback).toHaveBeenLastCalledWith("card-mock-1", false);
    await waitFor(() => expect(useless.getAttribute("aria-pressed")).toBe("true"));
    expect(useful.getAttribute("aria-pressed")).toBe("false");
  });

  it("keeps the previous choice when feedback is not saved", async () => {
    const onFeedback = vi.fn(() => Promise.reject(new Error("offline")));
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} onFeedback={onFeedback} />);
    const useful = screen.getByRole("button", { name: "Полезно" });

    fireEvent.click(useful);

    expect((await screen.findByRole("status")).textContent).toBe("Отзыв не отправлен");
    expect(useful.getAttribute("aria-pressed")).toBe("false");
    expect(useful.hasAttribute("disabled")).toBe(false);
  });

  it("hides feedback without a handler", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    expect(screen.queryByRole("button", { name: "Полезно" })).toBeNull();
    expect(screen.queryByRole("button", { name: "Не полезно" })).toBeNull();
  });

  it("folds the detail blocks into an accordion when compact", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} compact />);

    const toggles = document.querySelectorAll(".insight-card [aria-expanded]");
    expect(toggles.length).toBe(5);
    expect(Array.from(toggles).every((toggle) => toggle.getAttribute("aria-expanded") === "false")).toBe(true);
    expect(document.querySelectorAll(".insight-card h4").length).toBe(6);
  });
});
