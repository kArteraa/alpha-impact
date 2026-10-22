import { cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TEST_USER, chooseOption, renderApp, signIn, stubApi } from "./testing";

const SECTIONS = [
  ["Главная", "/"],
  ["События", "/events"],
  ["Платежи", "/payments/new"],
  ["Депозиты", "/deposits/new"],
  ["Кредиты", "/loans"],
  ["Профиль", "/profile"],
];

async function renderShell() {
  renderApp();
  return screen.findByRole("navigation", { name: "Разделы" });
}

describe("Layout", () => {
  beforeEach(() => {
    signIn();
    stubApi({ "GET /api/clients": [200, ["U_1941", "U_9250"]] });
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("names the product in text without a bank logo", async () => {
    await renderShell();

    expect(document.querySelector(".brand")?.textContent).toBe("Alpha Impact");
    expect(document.querySelector(".brand img, .brand svg")).toBeNull();
  });

  it("offers the top navigation with events", async () => {
    const nav = await renderShell();

    const hrefs = within(nav)
      .getAllByRole("link")
      .map((link) => link.getAttribute("href"));
    expect(hrefs).toEqual(SECTIONS.map(([, href]) => href));
    for (const [name, href] of SECTIONS) {
      expect(within(nav).getByRole("link", { name }).getAttribute("href")).toBe(href);
    }
  });

  it("offers the companies the user may act for", async () => {
    await renderShell();

    fireEvent.click(screen.getByRole("combobox", { name: "Компания" }));

    const options = screen.getAllByRole("option").map((option) => option.textContent);
    expect(options).toEqual(["СООО «Северный опт»Счёт ·· 4417", "САО «СтройЛизинг»Счёт ·· 9032"]);
    expect(screen.getByRole("option", { name: /Северный опт/ }).getAttribute("aria-selected")).toBe("true");
  });

  it("names a company without a showcase card by its id", async () => {
    stubApi({ "GET /api/clients": [200, ["U_1"]] });

    renderApp();

    expect((await screen.findByText("U_1")).className).toBe("company-name");
  });

  it("shows how many events the company has next to the events link", async () => {
    await renderShell();

    expect(screen.getByRole("link", { name: "События" }).querySelector(".nav-count")?.textContent).toBe("4");

    chooseOption("Компания", /СтройЛизинг/);

    expect(screen.getByRole("link", { name: "События" }).querySelector(".nav-count")?.textContent).toBe("3");
  });

  it("switches the company and changes the feed", async () => {
    await renderShell();
    expect(screen.getByText("Логистика в убытке")).toBeTruthy();

    chooseOption("Компания", /СтройЛизинг/);

    expect(screen.queryByText("Логистика в убытке")).toBeNull();
    expect(screen.getByText("Цемент подорожал на 9%")).toBeTruthy();
  });

  it("sends a visitor without a session to the login screen", async () => {
    stubApi({ "GET /api/clients": [401, "no session"] });

    renderApp();

    expect(await screen.findByRole("heading", { name: "Вход" })).toBeTruthy();
  });

  it("sends a user who has not logged in here to the login screen", async () => {
    localStorage.clear();

    renderApp();

    expect(await screen.findByRole("heading", { name: "Вход" })).toBeTruthy();
  });

  it("asks for the role before the first screen", async () => {
    localStorage.clear();
    localStorage.setItem("alpha-impact.user", TEST_USER);

    renderApp();

    expect(await screen.findByRole("heading", { name: "Ваша роль" })).toBeTruthy();
  });

  it("says so when the companies cannot be loaded", async () => {
    stubApi({ "GET /api/clients": [500, "boom"] });

    renderApp();

    expect((await screen.findByRole("alert")).textContent).toBe("Не удалось загрузить компании");
  });
});
