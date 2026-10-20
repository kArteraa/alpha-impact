import { cleanup, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { renderApp } from "./testing";

const ROUTES: Array<[string, string]> = [
  ["/login", "Вход"],
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
  afterEach(cleanup);

  it.each(ROUTES)("renders %s with heading %s", (path, heading) => {
    renderApp(path);
    expect(screen.getByRole("heading", { level: 1, name: heading })).toBeTruthy();
  });

  it("login screen has the user field and submit button", () => {
    renderApp("/login");
    expect(screen.getByRole("textbox")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Войти" })).toBeTruthy();
  });
});
