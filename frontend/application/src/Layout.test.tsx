import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "./App";

function renderApp(path = "/") {
  render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

describe("Layout", () => {
  afterEach(cleanup);

  it("names the product in text without a bank logo", () => {
    renderApp();

    expect(screen.getByText("Alpha Impact").className).toContain("brand");
    expect(document.querySelector(".brand img, .brand svg")).toBeNull();
  });

  it("offers the side navigation", () => {
    renderApp();

    const nav = screen.getByRole("navigation", { name: "Разделы" });
    const links = Array.from(nav.querySelectorAll("a"), (link) => [link.textContent, link.getAttribute("href")]);
    expect(links).toEqual([
      ["Главная", "/"],
      ["Платежи", "/payments/new"],
      ["Депозиты", "/deposits/new"],
      ["Кредиты", "/loans"],
      ["Профиль", "/profile"],
    ]);
  });

  it("switches the company and changes the feed", () => {
    renderApp();
    expect(screen.getByText("Логистика в убытке")).toBeTruthy();

    fireEvent.change(screen.getByLabelText("Компания"), { target: { value: "client_construction" } });

    expect(screen.queryByText("Логистика в убытке")).toBeNull();
    expect(screen.getByText("Цемент подорожал на 9%")).toBeTruthy();
  });
});
