import { cleanup, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { TEST_CLIENT, renderApp, signIn, stubApi } from "./testing";

const ROUTES: Array<[string, string]> = [
  ["/login", "Вход"],
  ["/role", "Ваша роль"],
  ["/", "Главный экран"],
  ["/payments/new", "Новый платёж"],
  ["/deposits/new", "Новый депозит"],
  ["/loans", "Кредиты"],
  ["/profile", "Профиль компании"],
  ["/trace/trace-mock-1", "Трасса trace-mock-1"],
  ["/events", "Все события"],
  ["/showcase", "Витрина InsightPanel"],
];

describe("routing", () => {
  beforeEach(() => {
    signIn();
    stubApi({
      "GET /api/clients": [200, [TEST_CLIENT]],
      [`GET /api/profile/${TEST_CLIENT}`]: [200, { client_id: TEST_CLIENT, features: {} }],
    });
  });

  afterEach(() => {
    cleanup();
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it.each(ROUTES)("renders %s with heading %s", async (path, heading) => {
    renderApp(path);
    expect(await screen.findByRole("heading", { level: 1, name: heading })).toBeTruthy();
  });

  it("login screen has the user field and submit button", () => {
    renderApp("/login");
    expect(screen.getByRole("textbox")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Войти" })).toBeTruthy();
  });
});
