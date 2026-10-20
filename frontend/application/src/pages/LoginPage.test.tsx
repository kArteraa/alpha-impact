import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { LoginPage } from "./LoginPage";

function renderLogin() {
  render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<h1>Главный экран</h1>} />
      </Routes>
    </MemoryRouter>,
  );
}

function submit(userId: string) {
  fireEvent.change(screen.getByLabelText("Тестовый пользователь"), { target: { value: userId } });
  fireEvent.click(screen.getByRole("button", { name: "Войти" }));
}

describe("LoginPage", () => {
  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("logs in through /auth/mock and opens the main screen", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ user_id: "user_cfo_wholesale" })));
    vi.stubGlobal("fetch", fetchMock);
    renderLogin();

    submit("user_cfo_wholesale");

    expect(await screen.findByRole("heading", { name: "Главный экран" })).toBeTruthy();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/mock");
  });

  it("shows the status when the login fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("unknown user", { status: 404 })));
    renderLogin();

    submit("nobody");

    expect((await screen.findByRole("alert")).textContent).toBe("Вход не удался (404)");
  });
});
