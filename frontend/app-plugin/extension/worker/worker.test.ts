import { describe, expect, it, vi } from "vitest";
import type { PageContext } from "../../src";
import { mockResponses } from "../../src/mocks";
import { CACHE_TTL_MS } from "../config";
import { ApiError, type ExtensionApi, NetworkError } from "./api";
import type { Store } from "./store";
import { createWorker } from "./worker";

const NOW = Date.parse("2026-10-23T12:00:00Z");
const TOKEN_TTL_MS = 2 * CACHE_TTL_MS;
const page: PageContext = { url: "https://news.test/rate", text: "ЦБ поднял ключевую ставку" };
const allPages = { article: true, counterparty: true, tender: true, fx_rate: true };

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
      expires_at: new Date(NOW + TOKEN_TTL_MS).toISOString(),
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

    expect(await worker({ type: "state" })).toEqual({ ok: true, value: { signedIn: false } });
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
    const order = [api.authMock, api.extensionToken, api.clients].map((call) => call.mock.invocationCallOrder[0]);
    expect(order).toEqual([...order].sort((a, b) => a - b));
  });

  it("reports a failed login with its status and stays signed out", async () => {
    const { api, worker } = setup();
    api.extensionToken.mockRejectedValueOnce(new ApiError(501, "Not implemented: AH-37"));

    expect(await worker({ type: "login", userId: "user_cfo" })).toEqual({ ok: false, error: "http", status: 501 });
    expect(await worker({ type: "state" })).toEqual({ ok: true, value: { signedIn: false } });
  });

  it("reports an unreachable server", async () => {
    const { api, worker } = setup();
    api.authMock.mockRejectedValueOnce(new NetworkError("Failed to fetch"));

    expect(await worker({ type: "login", userId: "user_cfo" })).toEqual({ ok: false, error: "network" });
  });

  it("signs out when the token expires", async () => {
    const { advance, worker } = await signedInAs();
    advance(TOKEN_TTL_MS);

    expect(await worker({ type: "state" })).toEqual({ ok: true, value: { signedIn: false } });
    expect(await worker({ type: "interpret", page })).toEqual({ ok: false, error: "signed_out" });
  });

  it("refuses to change settings when signed out", async () => {
    const { worker } = setup();

    expect(await worker({ type: "settings", patch: { role: "cfo" } })).toEqual({ ok: false, error: "signed_out" });
  });

  it("keeps settings per user across worker restarts", async () => {
    const { make, worker } = await signedInAs();
    const autoshow = { ...allPages, tender: false };
    await worker({ type: "settings", patch: { clientId: "U_9250", role: "treasurer", autoshow } });

    const restarted = make();
    const reply = await restarted({ type: "state" });
    await restarted({ type: "login", userId: "user_owner" });
    const other = await restarted({ type: "state" });

    expect(reply.ok && reply.value.signedIn && reply.value.settings).toEqual({
      clientId: "U_9250",
      role: "treasurer",
      autoshow,
    });
    expect(other.ok && other.value.signedIn && other.value.settings).toEqual({
      clientId: "U_1941",
      role: null,
      autoshow: allPages,
    });
  });

  it("logout forgets the token and the cached cards", async () => {
    const { api, worker } = await signedInAs();
    await worker({ type: "interpret", page });

    expect(await worker({ type: "logout" })).toEqual({ ok: true, value: { signedIn: false } });
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

  it("signs out when the API rejects the token", async () => {
    const { api, worker } = await signedInAs();
    api.interpret.mockRejectedValueOnce(new ApiError(401, "expired"));

    expect(await worker({ type: "interpret", page })).toEqual({ ok: false, error: "signed_out" });
    expect(await worker({ type: "state" })).toEqual({ ok: true, value: { signedIn: false } });
  });
});
