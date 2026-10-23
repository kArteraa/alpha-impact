import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router";
import { afterEach, describe, expect, it, vi } from "vitest";
import { loadUser, saveRole } from "../session/storage";
import { LoginPage } from "./LoginPage";

function renderLogin() {
  render(
    <MemoryRouter initialEntries={["/login"]}>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/role" element={<h1>Ваша роль</h1>} />
        <Route path="/profile" element={<h1>Профиль компании</h1>} />
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
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("marks the test mode", () => {
    renderLogin();

    expect(screen.getByText("Тестовый режим")).toBeTruthy();
  });

  it("logs in through /auth/mock and asks for the role on the first visit", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ user_id: "user_cfo_wholesale" })));
    vi.stubGlobal("fetch", fetchMock);
    renderLogin();

    submit("user_cfo_wholesale");

    expect(await screen.findByRole("heading", { name: "Ваша роль" })).toBeTruthy();
    expect(fetchMock.mock.calls[0][0]).toBe("/api/auth/mock");
    expect(loadUser()).toBe("user_cfo_wholesale");
  });

  it("goes straight to the profile confirmation when the role is known", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(JSON.stringify({ user_id: "user_cfo_wholesale" }))));
    saveRole("user_cfo_wholesale", "treasurer");
    renderLogin();

    submit("user_cfo_wholesale");

    expect(await screen.findByRole("heading", { name: "Профиль компании" })).toBeTruthy();
  });

  it("trims the user id before logging in", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ user_id: "user_cfo_wholesale" })));
    vi.stubGlobal("fetch", fetchMock);
    renderLogin();

    submit("  user_cfo_wholesale ");

    await screen.findByRole("heading", { name: "Ваша роль" });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({ user_id: "user_cfo_wholesale" });
  });

  it("does not log in with a blank user id", () => {
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    renderLogin();

    submit("   ");

    expect(screen.getByRole<HTMLButtonElement>("button", { name: "Войти" }).disabled).toBe(true);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("shows the status when the login fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("unknown user", { status: 404 })));
    renderLogin();

    submit("nobody");

    expect((await screen.findByRole("alert")).textContent).toBe("Вход не удался (404)");
  });
});
