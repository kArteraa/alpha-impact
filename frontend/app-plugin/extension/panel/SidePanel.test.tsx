import { act, cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { INTERPRET_DELAY_MS, type InterpretResponse } from "../../src";
import { mockResponses } from "../../src/mocks";
import { AUTOSHOW_DEFAULT } from "../config";
import type { DetectedPage, ExtensionState, Result, Send, Settings, WorkerRequest } from "../messages";
import { type PanelHost, SidePanel } from "./SidePanel";

const HEADLINE = "Логистика в убытке: платёж перевозчику";
const UNRECOGNISED = "Молчу: страница не похожа на статью, карточку контрагента, тендер или курс валют";

const article: DetectedPage = {
  pageType: "article",
  page: { url: "https://www.kommersant.ru/doc/1", text: "ЦБ повысил ключевую ставку\nТекст статьи", entities: [] },
};
const company: DetectedPage = {
  pageType: "counterparty",
  page: { url: "https://www.rusprofile.ru/id/1", text: "ООО «ТрансЛогистик»\nИНН 7707083893", entities: ["inn:7707083893"] },
};

function signedIn(settings: Partial<Settings> = {}): ExtensionState {
  return {
    signedIn: true,
    userId: "user_cfo",
    clients: ["U_1941", "U_9250"],
    settings: { clientId: "U_1941", role: "cfo", autoshow: AUTOSHOW_DEFAULT, ...settings },
  };
}

function panelWith(
  state: ExtensionState,
  detected: DetectedPage | null | Promise<DetectedPage | null>,
  interpret: Result<InterpretResponse> = { ok: true, value: mockResponses.cards },
) {
  const world = { state, detected };
  const listeners = new Set<() => void>();
  const send = vi.fn(async (request: WorkerRequest) => (request.type === "state" ? world.state : interpret));
  const host: PanelHost = {
    activePage: async () => world.detected,
    subscribe: (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
  render(<SidePanel send={send as unknown as Send} host={host} />);
  return {
    send,
    interprets: () => send.mock.calls.filter(([request]) => request.type === "interpret"),
    change: (next: Partial<typeof world>) => {
      Object.assign(world, next);
      act(() => listeners.forEach((listener) => listener()));
    },
  };
}

describe("SidePanel", () => {
  afterEach(cleanup);

  it("asks to sign in first", async () => {
    const { interprets } = panelWith({ signedIn: false }, article);

    expect(await screen.findByText("Войдите в расширение: нажмите на значок Alpha Impact")).toBeTruthy();
    expect(interprets()).toEqual([]);
  });

  it("asks to choose a role first", async () => {
    const { interprets } = panelWith(signedIn({ role: null }), article);

    expect(await screen.findByText("Выберите компанию и роль в окне расширения")).toBeTruthy();
    expect(interprets()).toEqual([]);
  });

  it.each([
    ["a business media article", article],
    ["a counterparty page", company],
  ])("shows the card for the chosen company on %s", async (_name, detected) => {
    const { send } = panelWith(signedIn(), detected);

    expect(await screen.findByText(HEADLINE)).toBeTruthy();
    expect(send).toHaveBeenCalledWith({ type: "interpret", page: detected.page });
  });

  it("stays silent on an unrecognised page without asking for a card", async () => {
    const { interprets } = panelWith(signedIn(), null);

    expect((await screen.findByRole("status")).textContent).toBe(UNRECOGNISED);
    expect(interprets()).toEqual([]);
  });

  it("admits a failed request and offers to retry", async () => {
    panelWith(signedIn(), article, { ok: false, error: "network" });

    expect(await screen.findByRole("button", { name: "Попробовать ещё раз" })).toBeTruthy();
  });

  it("follows the active tab to an unrecognised page", async () => {
    const { change } = panelWith(signedIn(), article);
    await screen.findByText(HEADLINE);

    change({ detected: null });

    expect(await screen.findByText(UNRECOGNISED)).toBeTruthy();
  });

  it("keeps the latest tab when an earlier answer comes late", async () => {
    let late: (detected: DetectedPage) => void = () => {};
    const { change, interprets } = panelWith(signedIn(), new Promise((resolve) => (late = resolve)));

    change({ detected: null });
    await screen.findByText(UNRECOGNISED);
    await act(async () => late(article));

    expect(screen.queryByText(UNRECOGNISED)).toBeTruthy();
    expect(interprets()).toEqual([]);
  });

  it("keeps the card when only the text of the same page changes", async () => {
    const { change, interprets } = panelWith(signedIn(), article);
    await screen.findByText(HEADLINE);

    change({ detected: { ...article, page: { ...article.page, text: `${article.page.text}\nОбновлено 1 мин назад` } } });
    await new Promise((resolve) => setTimeout(resolve, INTERPRET_DELAY_MS * 2));

    expect(interprets()).toHaveLength(1);
    expect(screen.getByText(HEADLINE)).toBeTruthy();
  });

  it("keeps the card when a setting the panel does not use changes", async () => {
    const { change, interprets } = panelWith(signedIn(), article);
    await screen.findByText(HEADLINE);

    change({
      state: signedIn({ autoshow: { ...AUTOSHOW_DEFAULT, tender: false } }),
      detected: { ...article, page: { ...article.page, text: `${article.page.text}
Обновлено 2 мин назад` } },
    });
    await new Promise((resolve) => setTimeout(resolve, INTERPRET_DELAY_MS * 2));

    expect(interprets()).toHaveLength(1);
  });

  it("asks again when another company is chosen", async () => {
    const { change, interprets } = panelWith(signedIn(), article);
    await screen.findByText(HEADLINE);

    change({ state: signedIn({ clientId: "U_9250" }) });

    await waitFor(() => expect(interprets()).toHaveLength(2));
  });

  it("asks to sign in again when the session ends", async () => {
    const { change } = panelWith(signedIn(), article);
    await screen.findByText(HEADLINE);

    change({ state: { signedIn: false } });

    expect(await screen.findByText("Войдите в расширение: нажмите на значок Alpha Impact")).toBeTruthy();
  });
});
