import type { InterpretResponse, PageContext } from "../../src";
import { AUTOSHOW_DEFAULT } from "../config";
import type { ExtensionState, Send, Settings, WorkerReply, WorkerRequest } from "../messages";
import { ApiError, type ExtensionApi, NetworkError } from "./api";
import { type CacheEntries, cacheKey, readCached, writeCached } from "./cache";
import type { Store } from "./store";

const SESSION_KEY = "session";
const CACHE_KEY = "cache";
const UNAUTHORIZED = 401;

interface Session {
  userId: string;
  token: string;
  expiresAt: string;
  clients: string[];
}

export interface WorkerDeps {
  api: ExtensionApi;
  session: Store;
  local: Store;
  now: () => number;
}

const SIGNED_OUT: ExtensionState = { signedIn: false };
const SIGNED_OUT_REPLY = { ok: false, error: "signed_out" } as const;

function ok<T>(value: T): WorkerReply<T> {
  return { ok: true, value };
}

function failed(error: unknown): WorkerReply<never> {
  if (error instanceof ApiError) {
    return { ok: false, error: "http", status: error.status };
  }
  if (error instanceof NetworkError) {
    return { ok: false, error: "network" };
  }
  throw error;
}

function settingsKey(userId: string): string {
  return `settings.${userId}`;
}

export function createWorker({ api, session, local, now }: WorkerDeps): Send {
  async function current(): Promise<Session | null> {
    const stored = await session.get<Session>(SESSION_KEY);
    if (stored === undefined) {
      return null;
    }
    if (Date.parse(stored.expiresAt) <= now()) {
      await session.remove(SESSION_KEY);
      return null;
    }
    return stored;
  }

  async function settingsOf({ userId, clients }: Session): Promise<Settings> {
    const stored = await local.get<Settings>(settingsKey(userId));
    const clientId = clients.find((id) => id === stored?.clientId) ?? clients[0] ?? null;
    return { clientId, role: stored?.role ?? null, autoshow: stored?.autoshow ?? AUTOSHOW_DEFAULT };
  }

  async function state(): Promise<ExtensionState> {
    const active = await current();
    if (active === null) {
      return SIGNED_OUT;
    }
    return { signedIn: true, userId: active.userId, clients: active.clients, settings: await settingsOf(active) };
  }

  async function login(userId: string): Promise<ExtensionState> {
    const user = await api.authMock(userId);
    const { token, expires_at } = await api.extensionToken();
    const clients = await api.clients();
    const created: Session = { userId: user.user_id, token, expiresAt: expires_at, clients };
    await session.set(SESSION_KEY, created);
    return state();
  }

  async function logout(): Promise<ExtensionState> {
    await session.remove(SESSION_KEY);
    await session.remove(CACHE_KEY);
    return SIGNED_OUT;
  }

  async function updateSettings(patch: Partial<Settings>): Promise<WorkerReply<ExtensionState>> {
    const active = await current();
    if (active === null) {
      return SIGNED_OUT_REPLY;
    }
    await local.set(settingsKey(active.userId), { ...(await settingsOf(active)), ...patch });
    return ok(await state());
  }

  async function interpret(page: PageContext): Promise<WorkerReply<InterpretResponse>> {
    const active = await current();
    if (active === null) {
      return SIGNED_OUT_REPLY;
    }
    const { clientId, role } = await settingsOf(active);
    if (clientId === null || role === null) {
      return { ok: false, error: "setup" };
    }
    const key = cacheKey(active.userId, clientId, role, page.url);
    const entries = (await session.get<CacheEntries>(CACHE_KEY)) ?? {};
    const cached = readCached(entries, key, now());
    if (cached !== undefined) {
      return ok(cached);
    }
    try {
      const response = await api.interpret(active.token, {
        user_id: active.userId,
        client_id: clientId,
        role,
        action_context: { ...page, type: "page" },
      });
      await session.set(CACHE_KEY, writeCached(entries, key, response, now()));
      return ok(response);
    } catch (error) {
      if (error instanceof ApiError && error.status === UNAUTHORIZED) {
        await logout();
        return SIGNED_OUT_REPLY;
      }
      return failed(error);
    }
  }

  async function handle(request: WorkerRequest): Promise<WorkerReply<ExtensionState | InterpretResponse>> {
    switch (request.type) {
      case "state":
        return ok(await state());
      case "login":
        return login(request.userId).then(ok, failed);
      case "logout":
        return ok(await logout());
      case "settings":
        return updateSettings(request.patch);
      case "interpret":
        return interpret(request.page);
    }
  }

  return handle as Send;
}
