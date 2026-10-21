import { cleanup, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { RUB_WHOLE } from "../money";
import { renderWithCompany } from "../testing";
import { DashboardPage } from "./DashboardPage";

function widget() {
  return screen.getByRole("region", { name: "Что важно для вашего бизнеса" });
}

describe("DashboardPage", () => {
  afterEach(cleanup);

  it("starts with the feed widget", () => {
    renderWithCompany(<DashboardPage />);

    expect(document.querySelector(".dashboard-grid")?.firstElementChild).toBe(widget());
  });

  it("shows the three most significant events with why and source badges", () => {
    renderWithCompany(<DashboardPage />);

    const headlines = within(widget()).getAllByRole("heading", { level: 3 }).map((heading) => heading.textContent);
    expect(headlines).toEqual(["Логистика в убытке", "Банк ждёт снижения ключевой ставки", "Юань дорожает к рублю"]);
    expect(within(widget()).getByText("43% ваших платежей уходит перевозчикам и складам")).toBeTruthy();
    expect(within(widget()).getAllByLabelText("Банк").length).toBeGreaterThan(0);
  });

  it("links to all events", () => {
    renderWithCompany(<DashboardPage />);

    expect(within(widget()).getByRole("link", { name: "Все события" }).getAttribute("href")).toBe("/events");
  });

  it("sums up deposits and loans on their tiles", () => {
    renderWithCompany(<DashboardPage />);

    expect(screen.getByRole("link", { name: /^Депозит/ }).textContent).toContain("до 15,2%");
    const loans = screen.getByRole("link", { name: /^Кредиты/ }).textContent;
    expect(loans).toContain(RUB_WHOLE.format(173_400_000));
    expect(loans).toContain("в портфеле · 3 продукта");
  });

  it.each([
    ["Платёж", "/payments/new"],
    ["Депозит", "/deposits/new"],
    ["Кредиты", "/loans"],
  ])("links the %s quick action to %s", (name, href) => {
    renderWithCompany(<DashboardPage />);

    expect(screen.getByRole("link", { name: new RegExp(`^${name}`) }).getAttribute("href")).toBe(href);
  });
});
