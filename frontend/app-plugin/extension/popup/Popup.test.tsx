import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { ExtensionState, Send, WorkerRequest } from "../messages";
import { Popup } from "./Popup";

const allPages = { article: true, counterparty: true, tender: true, fx_rate: true };
const signedOut: ExtensionState = { signedIn: false };
const signedIn: ExtensionState = {
  signedIn: true,
  userId: "user_cfo",
  clients: ["U_1941", "U_9250"],
  settings: { clientId: "U_1941", role: null, autoshow: allPages },
};

function popupWith(state: ExtensionState, replies: Partial<Record<WorkerRequest["type"], unknown>> = {}) {
  const send = vi.fn(async (request: WorkerRequest) =>
    request.type === "state" ? { ok: true, value: state } : (replies[request.type] ?? { ok: true, value: signedIn }),
  );
  render(<Popup send={send as unknown as Send} />);
  return send;
}

function select(label: string) {
  return screen.getByLabelText<HTMLSelectElement>(label);
}

describe("Popup", () => {
  afterEach(cleanup);

  it("logs in with a test user", async () => {
    const send = popupWith(signedOut);

    fireEvent.change(await screen.findByPlaceholderText("user_cfo_wholesale"), { target: { value: " user_cfo " } });
    fireEvent.click(screen.getByRole("button", { name: "Войти" }));

    expect(send).toHaveBeenCalledWith({ type: "login", userId: "user_cfo" });
    expect(await screen.findByLabelText("Компания")).toBeTruthy();
  });

  it("explains a failed login", async () => {
    popupWith(signedOut, { login: { ok: false, error: "http", status: 501 } });

    fireEvent.change(await screen.findByPlaceholderText("user_cfo_wholesale"), { target: { value: "user_cfo" } });
    fireEvent.click(screen.getByRole("button", { name: "Войти" }));

    expect((await screen.findByRole("alert")).textContent).toBe("Вход не удался (501)");
  });

  it("says when the server is unreachable", async () => {
    popupWith(signedOut, { login: { ok: false, error: "network" } });

    fireEvent.change(await screen.findByPlaceholderText("user_cfo_wholesale"), { target: { value: "user_cfo" } });
    fireEvent.click(screen.getByRole("button", { name: "Войти" }));

    expect((await screen.findByRole("alert")).textContent).toBe("Сервер недоступен");
  });

  it("shows company names and saves the chosen company", async () => {
    const send = popupWith(signedIn);

    const companies = await screen.findByLabelText<HTMLSelectElement>("Компания");
    expect(Array.from(companies.options, (option) => option.textContent)).toEqual([
      "ООО «Северный опт»",
      "АО «СтройЛизинг»",
    ]);
    fireEvent.change(companies, { target: { value: "U_9250" } });

    expect(send).toHaveBeenCalledWith({ type: "settings", patch: { clientId: "U_9250" } });
  });

  it("asks for a role and saves it", async () => {
    const send = popupWith(signedIn);

    await screen.findByLabelText("Роль");
    expect(select("Роль").selectedOptions[0].textContent).toBe("Выберите роль");
    fireEvent.change(select("Роль"), { target: { value: "treasurer" } });

    expect(send).toHaveBeenCalledWith({ type: "settings", patch: { role: "treasurer" } });
  });

  it("toggles auto-show per page type", async () => {
    const send = popupWith(signedIn);

    const tenders = await screen.findByLabelText<HTMLInputElement>("Тендеры и закупки");
    expect(screen.getAllByRole("checkbox").map((box) => (box as HTMLInputElement).checked)).toEqual([
      true,
      true,
      true,
      true,
    ]);
    fireEvent.click(tenders);

    expect(send).toHaveBeenCalledWith({ type: "settings", patch: { autoshow: { ...allPages, tender: false } } });
  });

  it("logs out", async () => {
    const send = popupWith(signedIn, { logout: { ok: true, value: signedOut } });

    fireEvent.click(await screen.findByRole("button", { name: "Выйти" }));

    expect(send).toHaveBeenCalledWith({ type: "logout" });
    expect(await screen.findByPlaceholderText("user_cfo_wholesale")).toBeTruthy();
  });

  it("returns to login when the session has ended", async () => {
    popupWith(signedIn, { settings: { ok: false, error: "signed_out" } });

    fireEvent.change(await screen.findByLabelText("Роль"), { target: { value: "cfo" } });

    await waitFor(() => expect(screen.getByPlaceholderText("user_cfo_wholesale")).toBeTruthy());
  });
});
