import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
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

  it("keeps the card and shows progress while a new answer is pending", () => {
    const { rerender } = render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);
    const shown = document.querySelector(".insight-card");

    rerender(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} pending />);

    expect(document.querySelector(".insight-card")).toBe(shown);
    expect(screen.getByRole("progressbar")).toBeTruthy();
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

  it("shows significance as dots, not a number", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    const dots = screen.getByLabelText("Значимость 3 из 3");
    expect(dots.querySelectorAll(".insight-dot-on").length).toBe(3);
  });

  it("marks every claim with a labelled badge that leads to its source", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    expect(screen.getAllByLabelText(/^Факт — источник: /).length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText(/^Банк — источник: /).length).toBeGreaterThan(0);
    expect(screen.getAllByLabelText(/^AI — источник: /).length).toBeGreaterThan(0);
    const newsBadge = screen.getByLabelText("Факт — источник: Склады маркетплейсов и перевозчики ушли в убыток");
    expect(newsBadge.getAttribute("href")).toBe("https://example.com/news/logistics");
  });

  it("highlights company traits as chips in the why block", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    const why = screen.getByRole("region", { name: "Почему это важно для вас" });
    expect(within(why).getByText("43% платежей — логистика").className).toContain("chip");
    expect(within(why).getByText("лизинг").className).toContain("chip");
  });

  it("collapses what happened and dates the bank view", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    const details = document.querySelectorAll(".insight-card details");
    expect(details.length).toBe(1);
    expect(details[0].hasAttribute("open")).toBe(false);
    const bank = screen.getByRole("region", { name: "Как это оценивает банк" });
    expect(within(bank).getByText(/07\.09\.2026/)).toBeTruthy();
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

  it("links the trace, takes feedback and asks a follow-up", () => {
    const onFollowup = vi.fn();
    render(
      <InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} onFollowup={onFollowup} />,
    );

    expect(screen.getByText("Как получен вывод").getAttribute("href")).toBe("/trace/trace-mock-1");
    const useful = screen.getByRole("button", { name: "Полезно" });
    fireEvent.click(useful);
    expect(useful.getAttribute("aria-pressed")).toBe("true");
    expect(screen.getByRole("button", { name: "Не полезно" }).getAttribute("aria-pressed")).toBe("false");
    fireEvent.click(screen.getByRole("button", { name: "Задать вопрос" }));
    expect(onFollowup).toHaveBeenCalledWith("card-mock-1");
  });

  it("hides the follow-up button without a handler", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} />);

    expect(screen.queryByRole("button", { name: "Задать вопрос" })).toBeNull();
  });

  it("folds the detail blocks into an accordion when compact", () => {
    render(<InsightPanel actionContext={context} role="cfo" response={mockResponses.cards} compact />);

    const details = document.querySelectorAll(".insight-card details");
    expect(details.length).toBe(5);
    expect(Array.from(details).some((block) => block.hasAttribute("open"))).toBe(false);
  });
});
