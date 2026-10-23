import { cleanup, fireEvent, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TEST_USER, answerFeed, chooseOption, renderApp, signIn, stubApi } from "./testing";

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
    stubApi({ "GET /api/clients": [200, ["U_1941", "U_9250"]], "POST /api/interpret": answerFeed });
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

  it("shows how many events the company feed has next to the events link", async () => {
    await renderShell();
    const count = () => screen.getByRole("link", { name: "События" }).querySelector(".nav-count")?.textContent;

    await waitFor(() => expect(count()).toBe("4"));

    chooseOption("Компания", /СтройЛизинг/);

    await waitFor(() => expect(count()).toBe("3"));
  });

  it("switches the company and shows its own feed on the same screen", async () => {
    const fetchMock = stubApi({ "GET /api/clients": [200, ["U_1941", "U_9250"]], "POST /api/interpret": answerFeed });
    await renderShell();
    expect(await screen.findByText("Логистика в убытке")).toBeTruthy();

    chooseOption("Компания", /СтройЛизинг/);

    expect(await screen.findByText("Цемент подорожал на 9%")).toBeTruthy();
    expect(screen.queryByText("Логистика в убытке")).toBeNull();
    const asked = fetchMock.mock.calls
      .filter(([url]) => url === "/api/interpret")
      .map(([, init]) => JSON.parse(String(init?.body)));
    expect(asked.map((body) => [body.client_id, body.action_context.type])).toEqual([
      ["U_1941", "dashboard"],
      ["U_9250", "dashboard"],
    ]);
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
    expect(screen.getByRole("link", { name: "Войти заново" }).getAttribute("href")).toBe("/login");
    expect(document.querySelector(".brand")?.textContent).toBe("Alpha Impact");
  });

  it("offers to log in again to a user without companies", async () => {
    stubApi({ "GET /api/clients": [200, []] });

    renderApp();

    expect((await screen.findByRole("alert")).textContent).toBe("Нет компаний, доступных этому пользователю");
    expect(screen.getByRole("link", { name: "Войти заново" }).getAttribute("href")).toBe("/login");
  });

  it("keeps the brand on screen while the companies load", () => {
    vi.stubGlobal("fetch", vi.fn(() => new Promise(() => {})));

    renderApp();

    expect(document.querySelector(".brand")?.textContent).toBe("Alpha Impact");
  });

  it("sends the user to the login screen when any request finds the session expired", async () => {
    stubApi({ "GET /api/clients": [200, ["U_1941"]], "GET /api/profile/U_1941": [401, "no session"] });

    renderApp("/profile");

    expect(await screen.findByRole("heading", { name: "Вход" })).toBeTruthy();
    expect(localStorage.getItem("alpha-impact.user")).toBeNull();
  });
});
