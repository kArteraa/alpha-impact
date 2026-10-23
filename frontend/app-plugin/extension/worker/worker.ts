import type { InterpretResponse, PageContext } from "../../src";
import { AUTOSHOW_DEFAULT } from "../config";
import type { ExtensionState, Result, Send, Settings, SettingsPatch, WorkerRequest } from "../messages";
import { ApiError, type ExtensionApi, NetworkError } from "./api";
import { type CacheEntries, cacheKey, readCached, writeCached } from "./cache";
import type { Store } from "./store";

const SESSION_KEY = "session";
const CACHE_KEY = "cache";

interface Session {
  userId: string;
  token: string;
  expiresAt: string;
  clients: string[];
}

interface WorkerDeps {
  api: ExtensionApi;
  session: Store;
  local: Store;
  now: () => number;
}

const SIGNED_OUT: ExtensionState = { signedIn: false };
const SIGNED_OUT_REPLY = { ok: false, error: "signed_out" } as const;

function ok<T>(value: T): Result<T> {
  return { ok: true, value };
}

function failed(error: unknown): Result<never> {
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

function resolve(stored: SettingsPatch | undefined, clients: string[]): Settings {
  return {
    clientId: clients.find((id) => id === stored?.clientId) ?? clients[0] ?? null,
    role: stored?.role ?? null,
    autoshow: { ...AUTOSHOW_DEFAULT, ...stored?.autoshow },
  };
}

function signedIn(active: Session, settings: Settings): ExtensionState {
  return { signedIn: true, userId: active.userId, clients: active.clients, settings };
}

export function createWorker({ api, session, local, now }: WorkerDeps): Send {
  async function endSession(): Promise<ExtensionState> {
    await session.remove(SESSION_KEY);
    await session.remove(CACHE_KEY);
    return SIGNED_OUT;
  }

  async function current(): Promise<Session | null> {
    const stored = await session.get<Session>(SESSION_KEY);
    if (stored !== undefined && Date.parse(stored.expiresAt) <= now()) {
      await endSession();
      return null;
    }
    return stored ?? null;
  }

  async function settingsOf(active: Session): Promise<Settings> {
    return resolve(await local.get<SettingsPatch>(settingsKey(active.userId)), active.clients);
  }

  async function state(): Promise<ExtensionState> {
    const active = await current();
    return active === null ? SIGNED_OUT : signedIn(active, await settingsOf(active));
  }

  async function login(userId: string): Promise<ExtensionState> {
    const user = await api.authMock(userId);
    const [{ token, expires_at }, clients] = await Promise.all([api.extensionToken(), api.clients()]);
    const created: Session = { userId: user.user_id, token, expiresAt: expires_at, clients };
    await session.set(SESSION_KEY, created);
    return signedIn(created, await settingsOf(created));
  }

  async function updateSettings(patch: SettingsPatch): Promise<ExtensionState> {
    const active = await current();
    if (active === null) {
      return SIGNED_OUT;
    }
    const previous = await settingsOf(active);
    const autoshow = { ...previous.autoshow, ...patch.autoshow };
    const settings = resolve({ ...previous, ...patch, autoshow }, active.clients);
    await local.set(settingsKey(active.userId), settings);
    return signedIn(active, settings);
  }

  async function interpret(page: PageContext): Promise<Result<InterpretResponse>> {
    const active = await current();
    if (active === null) {
      return SIGNED_OUT_REPLY;
    }
    const [{ clientId, role }, entries = {}] = await Promise.all([
      settingsOf(active),
      session.get<CacheEntries>(CACHE_KEY),
    ]);
    if (clientId === null || role === null) {
      return { ok: false, error: "setup" };
    }
    const key = cacheKey(active.userId, clientId, role, page.url);
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
      if (error instanceof ApiError && error.status === 401) {
        await endSession();
        return SIGNED_OUT_REPLY;
      }
      return failed(error);
    }
  }

  function handle(request: WorkerRequest): Promise<ExtensionState | Result<ExtensionState | InterpretResponse>> {
    switch (request.type) {
      case "state":
        return state();
      case "login":
        return login(request.userId).then(ok, failed);
      case "logout":
        return endSession();
      case "settings":
        return updateSettings(request.patch);
      case "interpret":
        return interpret(request.page);
    }
  }

  return handle as Send;
}
