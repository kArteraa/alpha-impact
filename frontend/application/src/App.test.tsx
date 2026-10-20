import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router";
import { afterEach, describe, expect, it } from "vitest";
import { App } from "./App";

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
    render(
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("heading", { level: 1, name: heading })).toBeTruthy();
  });

  it("login screen has the user field and submit button", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>,
    );
    expect(screen.getByRole("textbox")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Войти" })).toBeTruthy();
  });
});
