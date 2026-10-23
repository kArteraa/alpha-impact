import type { InterpretState } from "@alpha-impact/plugin";
import { cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { SILENT_FEED } from "../dashboard/events.fixture";
import { RUB_WHOLE } from "../money";
import { renderWithCompany } from "../testing";
import { DashboardPage } from "./DashboardPage";

function widget() {
  return screen.getByRole("region", { name: "Что изменилось вокруг ваших операций" });
}

function renderDashboard(feed: Partial<InterpretState> = {}) {
  return renderWithCompany(<DashboardPage />, { feed });
}

describe("DashboardPage", () => {
  afterEach(cleanup);

  it("starts with the feed widget", () => {
    renderDashboard();

    expect(document.querySelector(".dashboard-grid")?.firstElementChild).toBe(widget());
  });

  it("offers to paste a news item from the feed widget", () => {
    renderDashboard();

    expect(within(widget()).getByRole("link", { name: "Вставить новость" }).getAttribute("href")).toBe("/news/new");
  });

  it("shows the three most significant events with significance, a consequence and source badges", () => {
    renderDashboard();

    const headlines = within(widget()).getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
    expect(headlines).toEqual(["Логистика в убытке", "Банк ждёт снижения ключевой ставки", "Юань дорожает к рублю"]);
    expect(within(widget()).getAllByLabelText(/^Значимость \d из 3$/)).toHaveLength(3);
    expect(within(widget()).getByText("Перевозчики могут поднять тарифы: им уходит 43% платежей")).toBeTruthy();
    expect(within(widget()).getAllByLabelText("Банк").length).toBeGreaterThan(0);
  });

  it("marks the consequence phrase with the type of its own source", () => {
    renderDashboard();

    const logistics = within(widget()).getByRole("link", { name: "Логистика в убытке" }).closest("li");
    expect([...(logistics?.querySelectorAll(".claim-badge") ?? [])].map((badge) => badge.getAttribute("aria-label"))).toEqual([
      "Факт",
    ]);
  });

  it("opens the full card of an event", () => {
    renderDashboard();

    expect(within(widget()).getByRole("link", { name: "Логистика в убытке" }).getAttribute("href")).toBe(
      "/events/ev-logistics",
    );
  });

  it("links to all events", () => {
    renderDashboard();

    expect(within(widget()).getByRole("link", { name: "Все события" }).getAttribute("href")).toBe("/events");
  });

  it("shows that it is still looking for events", () => {
    renderDashboard({ response: undefined });

    expect(within(widget()).getByText("Смотрю новости и позицию банка")).toBeTruthy();
    expect(within(widget()).queryAllByRole("heading", { level: 3 })).toHaveLength(0);
  });

  it("offers to try again when the feed failed", () => {
    const retry = vi.fn();
    renderDashboard({ failed: true, retry });

    fireEvent.click(within(widget()).getByRole("button", { name: "Попробовать ещё раз" }));

    expect(retry).toHaveBeenCalledOnce();
  });

  it("says so explicitly when nothing important happened", () => {
    renderDashboard({ response: SILENT_FEED });

    expect(within(widget()).getByRole("status").textContent).toContain("Пока ничего важного для вашего бизнеса");
    expect(within(widget()).getByRole("link", { name: "Проверить профиль компании" }).getAttribute("href")).toBe(
      "/profile",
    );
  });

  it("sums up deposits and loans on their tiles", () => {
    renderDashboard();

    expect(screen.getByRole("link", { name: /^Депозит/ }).textContent).toContain("до 15,2%");
    const loans = screen.getByRole("link", { name: /^Кредиты/ }).textContent;
    expect(loans).toContain(RUB_WHOLE.format(173_400_000));
    expect(loans).toContain("в портфеле · 3 продукта");
  });

  it("shows the balance trend on the account tile", () => {
    renderDashboard();

    expect(screen.getByRole("img", { name: "Остаток за месяц" })).toBeTruthy();
    expect(document.querySelector(".account-change")?.textContent?.replace(/\s/g, " ")).toBe("+6,8 млн ₽ за месяц");
  });

  it("sums up money in and out by week", () => {
    renderDashboard();

    const cashflow = screen.getByRole("region", { name: "Движение денег" });
    expect(cashflow.textContent?.replace(/\s/g, " ")).toContain("Поступления364,1 млн ₽");
    const table = within(cashflow).getByRole("table", { name: /Поступления и списания по неделям/ });
    expect(within(table).getAllByRole("row").length).toBe(6);
  });

  it.each([
    ["Платёж", "/payments/new"],
    ["Депозит", "/deposits/new"],
    ["Кредиты", "/loans"],
  ])("links the %s quick action to %s", (name, href) => {
    renderDashboard();

    expect(screen.getByRole("link", { name: new RegExp(`^${name}`) }).getAttribute("href")).toBe(href);
  });
});
