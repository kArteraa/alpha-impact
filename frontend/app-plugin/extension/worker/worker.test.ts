import { describe, expect, it, vi } from "vitest";
import type { PageContext } from "../../src";
import { mockResponses } from "../../src/mocks";
import { CACHE_TTL_MS } from "../config";
import type { DetectedPage } from "../messages";
import { ApiError, type ExtensionApi, NetworkError } from "./api";
import type { Store } from "./store";
import { createWorker } from "./worker";

const NOW = Date.parse("2026-10-23T12:00:00Z");
const TOKEN_TTL_MS = 2 * CACHE_TTL_MS;
const page: PageContext = { url: "https://news.test/rate", text: "ЦБ поднял ключевую ставку" };
const article: DetectedPage = { pageType: "article", page };
const allPages = { article: true, counterparty: true, tender: true, fx_rate: true };
const signedOut = { signedIn: false };

function memoryStore() {
  const data = new Map<string, unknown>();
  const store: Store = {
    get: async <T,>(key: string) => data.get(key) as T | undefined,
    set: async (key, value) => {
      data.set(key, structuredClone(value));
    },
    remove: async (key) => {
      data.delete(key);
    },
  };
  return { data, store };
}

function setup() {
  let now = NOW;
  const api = {
    authMock: vi.fn<ExtensionApi["authMock"]>(async (userId) => ({ user_id: userId })),
    extensionToken: vi.fn<ExtensionApi["extensionToken"]>(async () => ({
      token: "t-1",
      expires_at: new Date(now + TOKEN_TTL_MS).toISOString(),
    })),
    clients: vi.fn<ExtensionApi["clients"]>(async () => ["U_1941", "U_9250"]),
    interpret: vi.fn<ExtensionApi["interpret"]>(async () => mockResponses.cards),
  };
  const session = memoryStore();
  const local = memoryStore();
  const make = () => createWorker({ api, session: session.store, local: local.store, now: () => now });
  return {
    api,
    session,
    worker: make(),
    make,
    advance: (ms: number) => {
      now += ms;
    },
  };
}

async function signedInAs(role: "cfo" | null = "cfo") {
  const context = setup();
  await context.worker({ type: "login", userId: "user_cfo" });
  if (role !== null) {
    await context.worker({ type: "settings", patch: { role } });
  }
  return context;
}

describe("extension worker session", () => {
  it("is signed out before login", async () => {
    const { worker } = setup();

    expect(await worker({ type: "state" })).toEqual(signedOut);
  });

  it("logs in with the mock session, then takes a token and the clients", async () => {
    const { api, worker } = setup();

    const reply = await worker({ type: "login", userId: "user_cfo" });

    expect(reply).toEqual({
      ok: true,
      value: {
        signedIn: true,
        userId: "user_cfo",
        clients: ["U_1941", "U_9250"],
        settings: { clientId: "U_1941", role: null, autoshow: allPages },
      },
    });
    expect(api.authMock).toHaveBeenCalledWith("user_cfo");
    expect(api.authMock).toHaveBeenCalledBefore(api.extensionToken);
    expect(api.authMock).toHaveBeenCalledBefore(api.clients);
  });

  it("reports a failed login with its status and stays signed out", async () => {
    const { api, worker } = setup();
    api.extensionToken.mockRejectedValueOnce(new ApiError(501, "Not implemented: AH-37"));

    expect(await worker({ type: "login", userId: "user_cfo" })).toEqual({ ok: false, error: "http", status: 501 });
    expect(await worker({ type: "state" })).toEqual(signedOut);
  });

  it("reports an unreachable server", async () => {
    const { api, worker } = setup();
    api.authMock.mockRejectedValueOnce(new NetworkError("Failed to fetch"));

    expect(await worker({ type: "login", userId: "user_cfo" })).toEqual({ ok: false, error: "network" });
  });

  it("signs out and forgets cached cards when the token expires", async () => {
    const { advance, api, worker } = await signedInAs();
    await worker({ type: "interpret", page });
    advance(TOKEN_TTL_MS);

    expect(await worker({ type: "state" })).toEqual(signedOut);
    expect(await worker({ type: "interpret", page })).toEqual({ ok: false, error: "signed_out" });

    await worker({ type: "login", userId: "user_cfo" });
    await worker({ type: "interpret", page });
    expect(api.interpret).toHaveBeenCalledTimes(2);
  });

  it("does not change settings when signed out", async () => {
    const { worker } = setup();

    expect(await worker({ type: "settings", patch: { role: "cfo" } })).toEqual(signedOut);
  });

  it("keeps settings per user across worker restarts", async () => {
    const { make, worker } = await signedInAs();
    await worker({ type: "settings", patch: { clientId: "U_9250", role: "treasurer" } });

    const restarted = make();
    const kept = await restarted({ type: "state" });
    await restarted({ type: "login", userId: "user_owner" });
    const other = await restarted({ type: "state" });

    expect(kept).toMatchObject({ settings: { clientId: "U_9250", role: "treasurer", autoshow: allPages } });
    expect(other).toMatchObject({ settings: { clientId: "U_1941", role: null, autoshow: allPages } });
  });

  it("merges auto-show changes one page type at a time", async () => {
    const { worker } = await signedInAs();

    await worker({ type: "settings", patch: { autoshow: { tender: false } } });
    const reply = await worker({ type: "settings", patch: { autoshow: { article: false } } });

    expect(reply).toMatchObject({ settings: { autoshow: { ...allPages, tender: false, article: false } } });
  });

  it("keeps the company within the user's clients", async () => {
    const { worker } = await signedInAs();

    expect(await worker({ type: "settings", patch: { clientId: "U_0000" } })).toMatchObject({
      settings: { clientId: "U_1941" },
    });
  });

  it("logout forgets the token and the cached cards", async () => {
    const { api, worker } = await signedInAs();
    await worker({ type: "interpret", page });

    expect(await worker({ type: "logout" })).toEqual(signedOut);
    await worker({ type: "login", userId: "user_cfo" });
    await worker({ type: "interpret", page });

    expect(api.interpret).toHaveBeenCalledTimes(2);
  });
});

describe("extension worker interpret", () => {
  it("refuses to interpret until a role is chosen", async () => {
    const { api, worker } = await signedInAs(null);

    expect(await worker({ type: "interpret", page })).toEqual({ ok: false, error: "setup" });
    expect(api.interpret).not.toHaveBeenCalled();
  });

  it("sends the page with the token, user, company and role", async () => {
    const { api, worker } = await signedInAs();

    expect(await worker({ type: "interpret", page })).toEqual({ ok: true, value: mockResponses.cards });
    expect(api.interpret).toHaveBeenCalledWith("t-1", {
      user_id: "user_cfo",
      client_id: "U_1941",
      role: "cfo",
      action_context: { ...page, type: "page" },
    });
  });

  it("serves the same URL from the cache for an hour", async () => {
    const { advance, api, worker } = await signedInAs();
    api.interpret.mockResolvedValueOnce(mockResponses.silent);

    await worker({ type: "interpret", page });
    advance(CACHE_TTL_MS - 1);
    expect(await worker({ type: "interpret", page: { ...page, text: "другой текст" } })).toEqual({
      ok: true,
      value: mockResponses.silent,
    });
    expect(api.interpret).toHaveBeenCalledTimes(1);

    advance(1);
    await worker({ type: "interpret", page });
    expect(api.interpret).toHaveBeenCalledTimes(2);
  });

  it("keeps separate cache entries per company, role and URL", async () => {
    const { api, worker } = await signedInAs();

    await worker({ type: "interpret", page });
    await worker({ type: "interpret", page: { ...page, url: "https://news.test/other" } });
    await worker({ type: "settings", patch: { clientId: "U_9250" } });
    await worker({ type: "interpret", page });
    await worker({ type: "settings", patch: { role: "treasurer" } });
    await worker({ type: "interpret", page });

    expect(api.interpret).toHaveBeenCalledTimes(4);
  });

  it("drops expired cards when it stores a new one", async () => {
    const { advance, session, worker } = await signedInAs();

    await worker({ type: "interpret", page });
    advance(CACHE_TTL_MS);
    await worker({ type: "interpret", page: { ...page, url: "https://news.test/other" } });

    expect(Object.keys(session.data.get("cache") as object)).toHaveLength(1);
  });

  it("does not cache failures", async () => {
    const { api, worker } = await signedInAs();
    api.interpret.mockRejectedValueOnce(new ApiError(500, "boom"));

    expect(await worker({ type: "interpret", page })).toEqual({ ok: false, error: "http", status: 500 });
    expect(await worker({ type: "interpret", page })).toEqual({ ok: true, value: mockResponses.cards });
    expect(api.interpret).toHaveBeenCalledTimes(2);
  });

  it("does not cache cards that need review", async () => {
    const { api, worker } = await signedInAs();
    const card = { ...mockResponses.cards.cards[0], needs_review: true };
    api.interpret.mockResolvedValueOnce({ ...mockResponses.cards, cards: [card] });

    await worker({ type: "interpret", page });
    await worker({ type: "interpret", page });

    expect(api.interpret).toHaveBeenCalledTimes(2);
  });

  it("does not bring cached cards back after a logout during the request", async () => {
    const { api, session, worker } = await signedInAs();
    let answer: (response: typeof mockResponses.cards) => void = () => {};
    api.interpret.mockReturnValueOnce(new Promise((resolve) => (answer = resolve)));

    const pending = worker({ type: "interpret", page });
    await worker({ type: "logout" });
    answer(mockResponses.cards);
    await pending;

    expect(session.data.has("cache")).toBe(false);
  });

  it("answers an unexpected failure instead of leaving the caller waiting", async () => {
    const { api, worker } = await signedInAs();
    vi.spyOn(console, "error").mockImplementation(() => {});
    api.interpret.mockRejectedValueOnce(new SyntaxError("Unexpected token <"));

    expect(await worker({ type: "interpret", page })).toEqual({ ok: false, error: "failed" });
  });

  it("treats a token without a readable expiry as expired", async () => {
    const { api, worker } = setup();
    api.extensionToken.mockResolvedValueOnce({ token: "t-1", expires_at: "" });

    await worker({ type: "login", userId: "user_cfo" });

    expect(await worker({ type: "state" })).toEqual(signedOut);
  });

  it("signs out when the API rejects the token", async () => {
    const { api, worker } = await signedInAs();
    api.interpret.mockRejectedValueOnce(new ApiError(401, "expired"));

    expect(await worker({ type: "interpret", page })).toEqual({ ok: false, error: "signed_out" });
    expect(await worker({ type: "state" })).toEqual(signedOut);
  });
});

describe("extension worker page report", () => {
  it("does not offer the notice before login", async () => {
    const { api, worker } = setup();

    expect(await worker({ type: "page", detected: article })).toBe(false);
    expect(api.interpret).not.toHaveBeenCalled();
  });

  it("does not offer the notice until a role is chosen", async () => {
    const { api, worker } = await signedInAs(null);

    expect(await worker({ type: "page", detected: article })).toBe(false);
    expect(api.interpret).not.toHaveBeenCalled();
  });

  it("does not read a page whose type has auto-show off", async () => {
    const { api, worker } = await signedInAs();
    await worker({ type: "settings", patch: { autoshow: { article: false } } });

    expect(await worker({ type: "page", detected: article })).toBe(false);
    expect(await worker({ type: "page", detected: { pageType: "counterparty", page } })).toBe(true);
    expect(api.interpret).toHaveBeenCalledTimes(1);
  });

  it("offers the notice when the page has cards", async () => {
    const { worker } = await signedInAs();

    expect(await worker({ type: "page", detected: article })).toBe(true);
  });

  it.each([
    ["silence", mockResponses.silent],
    ["no cards", { silent: false, silent_reason: null, cards: [], cached: false }],
  ])("does not offer the notice for %s", async (_name, response) => {
    const { api, worker } = await signedInAs();
    api.interpret.mockResolvedValueOnce(response);

    expect(await worker({ type: "page", detected: article })).toBe(false);
  });

  it("does not offer the notice for cards that need review, which are not kept for the panel", async () => {
    const { api, worker } = await signedInAs();
    const card = { ...mockResponses.cards.cards[0], needs_review: true };
    api.interpret.mockResolvedValueOnce({ ...mockResponses.cards, cards: [card] });

    expect(await worker({ type: "page", detected: article })).toBe(false);
  });

  it("does not offer the notice when the request fails", async () => {
    const { api, worker } = await signedInAs();
    api.interpret.mockRejectedValueOnce(new NetworkError("offline"));

    expect(await worker({ type: "page", detected: article })).toBe(false);
  });

  it("lets the panel show the same page from the cache", async () => {
    const { api, worker } = await signedInAs();

    expect(await worker({ type: "page", detected: article })).toBe(true);
    expect(await worker({ type: "interpret", page })).toEqual({ ok: true, value: mockResponses.cards });
    expect(api.interpret).toHaveBeenCalledTimes(1);
  });
});

describe("extension worker shared requests", () => {
  it("asks the API once when the notice and the panel read the same page together", async () => {
    const { api, worker } = await signedInAs();
    let answer: (response: typeof mockResponses.cards) => void = () => {};
    api.interpret.mockReturnValueOnce(new Promise((resolve) => (answer = resolve)));

    const notice = worker({ type: "page", detected: article });
    const panel = worker({ type: "interpret", page });
    await vi.waitFor(() => expect(api.interpret).toHaveBeenCalled());
    answer(mockResponses.cards);

    expect(await notice).toBe(true);
    expect(await panel).toEqual({ ok: true, value: mockResponses.cards });
    expect(api.interpret).toHaveBeenCalledTimes(1);
  });

  it("asks the API again after a shared request fails", async () => {
    const { api, worker } = await signedInAs();
    api.interpret.mockRejectedValueOnce(new NetworkError("offline"));

    await Promise.all([worker({ type: "interpret", page }), worker({ type: "interpret", page })]);
    await worker({ type: "interpret", page });

    expect(api.interpret).toHaveBeenCalledTimes(2);
  });
});
