import { cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { renderApp } from "./testing";

const SECTIONS = [
  ["Главная", "/"],
  ["События", "/events"],
  ["Платежи", "/payments/new"],
  ["Депозиты", "/deposits/new"],
  ["Кредиты", "/loans"],
  ["Профиль", "/profile"],
];

describe("Layout", () => {
  afterEach(cleanup);

  it("names the product in text without a bank logo", () => {
    renderApp();

    expect(document.querySelector(".brand")?.textContent).toBe("Alpha Impact");
    expect(document.querySelector(".brand img, .brand svg")).toBeNull();
  });

  it("offers the top navigation with events", () => {
    renderApp();

    const nav = screen.getByRole("navigation", { name: "Разделы" });
    const hrefs = within(nav)
      .getAllByRole("link")
      .map((link) => link.getAttribute("href"));
    expect(hrefs).toEqual(SECTIONS.map(([, href]) => href));
    for (const [name, href] of SECTIONS) {
      expect(within(nav).getByRole("link", { name }).getAttribute("href")).toBe(href);
    }
  });

  it("shows how many events the company has next to the events link", () => {
    renderApp();

    const events = screen.getByRole("link", { name: "События" });
    expect(events.querySelector(".nav-count")?.textContent).toBe("4");

    fireEvent.change(screen.getByLabelText("Компания"), { target: { value: "client_construction" } });

    expect(events.querySelector(".nav-count")?.textContent).toBe("3");
  });

  it("switches the company and changes the feed", () => {
    renderApp();
    expect(screen.getByText("Логистика в убытке")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Компания"), { target: { value: "client_construction" } });

    expect(screen.queryByText("Логистика в убытке")).toBeNull();
    expect(screen.getByText("Цемент подорожал на 9%")).toBeTruthy();
  });
});
