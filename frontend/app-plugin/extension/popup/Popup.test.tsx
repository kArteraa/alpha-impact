import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AUTOSHOW_DEFAULT } from "../config";
import type { ExtensionState, Send, WorkerRequest } from "../messages";
import { Popup } from "./Popup";

const signedOut: ExtensionState = { signedIn: false };
const signedIn: ExtensionState = {
  signedIn: true,
  userId: "user_cfo",
  clients: ["U_1941", "U_9250"],
  settings: { clientId: "U_1941", role: null, autoshow: AUTOSHOW_DEFAULT },
};

function popupWith(state: ExtensionState, replies: Partial<Record<WorkerRequest["type"], unknown>> = {}) {
  const send = vi.fn(async (request: WorkerRequest) =>
    request.type === "state" ? state : (replies[request.type] ?? signedIn),
  );
  render(<Popup send={send as unknown as Send} />);
  return send;
}

async function logInAs(userId: string) {
  fireEvent.change(await screen.findByPlaceholderText("user_cfo_wholesale"), { target: { value: userId } });
  fireEvent.click(screen.getByRole("button", { name: "Войти" }));
}

describe("Popup", () => {
  afterEach(cleanup);

  it("logs in with a test user", async () => {
    const send = popupWith(signedOut, { login: { ok: true, value: signedIn } });

    await logInAs(" user_cfo ");

    expect(send).toHaveBeenCalledWith({ type: "login", userId: "user_cfo" });
    expect(await screen.findByLabelText("Компания")).toBeTruthy();
  });

  it.each([
    [{ ok: false, error: "http", status: 501 }, "Вход не удался (501)"],
    [{ ok: false, error: "network" }, "Сервер недоступен"],
    [{ ok: false, error: "failed" }, "Вход не удался"],
  ])("explains a failed login %j", async (reply, text) => {
    popupWith(signedOut, { login: reply });

    await logInAs("user_cfo");

    expect((await screen.findByRole("alert")).textContent).toBe(text);
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

    const role = await screen.findByLabelText<HTMLSelectElement>("Роль");
    expect(role.selectedOptions[0].textContent).toBe("Выберите роль");
    fireEvent.change(role, { target: { value: "treasurer" } });

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

    expect(send).toHaveBeenCalledWith({ type: "settings", patch: { autoshow: { tender: false } } });
  });

  it("logs out", async () => {
    const send = popupWith(signedIn, { logout: signedOut });

    fireEvent.click(await screen.findByRole("button", { name: "Выйти" }));

    expect(send).toHaveBeenCalledWith({ type: "logout" });
    expect(await screen.findByPlaceholderText("user_cfo_wholesale")).toBeTruthy();
  });

  it("returns to login when the session has ended", async () => {
    popupWith(signedIn, { settings: signedOut });

    fireEvent.change(await screen.findByLabelText("Роль"), { target: { value: "cfo" } });

    await waitFor(() => expect(screen.getByPlaceholderText("user_cfo_wholesale")).toBeTruthy());
  });
});
