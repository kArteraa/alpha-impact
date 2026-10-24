import type { InterpretResponse, PageContext } from "../../src";
import { AUTOSHOW_DEFAULT } from "../config";
import type {
  DetectedPage,
  ExtensionState,
  Result,
  Send,
  Settings,
  SettingsPatch,
  WorkerRequest,
} from "../messages";
import { ApiError, type ExtensionApi, NetworkError } from "./api";
import { CACHE_KEY, type CacheEntries, cacheKey, readCached, writeCached } from "./cache";
import type { Store } from "./store";

const SESSION_KEY = "session";

interface Session {
  userId: string;
  token: string;
  expiresAt: string;
  clients: string[];
}

interface Context {
  active: Session;
  settings: Settings;
  entries: CacheEntries;
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
  console.error(error);
  return { ok: false, error: "failed" };
}

function reviewed(response: InterpretResponse): boolean {
  return !response.cards?.some((card) => card.needs_review);
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
  const running = new Map<string, Promise<InterpretResponse>>();

  function shared(key: string, request: () => Promise<InterpretResponse>): Promise<InterpretResponse> {
    const pending = running.get(key) ?? request().finally(() => running.delete(key));
    running.set(key, pending);
    return pending;
  }

  async function endSession(): Promise<ExtensionState> {
    await session.remove(SESSION_KEY);
    await session.remove(CACHE_KEY);
    return SIGNED_OUT;
  }

  async function current(): Promise<Session | null> {
    const stored = await session.get<Session>(SESSION_KEY);
    if (stored !== undefined && !(Date.parse(stored.expiresAt) > now())) {
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
    if (!(Date.parse(expires_at) > now())) {
      throw new Error(`Extension token expires at ${expires_at || "an unreadable time"}`);
    }
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

  async function remember(active: Session, key: string, response: InterpretResponse): Promise<void> {
    try {
      const latest = await session.get<Session>(SESSION_KEY);
      if (latest?.token !== active.token) {
        return;
      }
      const entries = (await session.get<CacheEntries>(CACHE_KEY)) ?? {};
      await session.set(CACHE_KEY, writeCached(entries, key, response, now()));
    } catch (error) {
      console.error(error);
    }
  }

  async function context(): Promise<Context | null> {
    const active = await current();
    if (active === null) {
      return null;
    }
    const [settings, entries = {}] = await Promise.all([
      settingsOf(active),
      session.get<CacheEntries>(CACHE_KEY),
    ]);
    return { active, settings, entries };
  }

  async function interpretIn(
    { active, settings, entries }: Context,
    page: PageContext,
  ): Promise<Result<InterpretResponse>> {
    const { clientId, role } = settings;
    if (clientId === null || role === null) {
      return { ok: false, error: "setup" };
    }
    const key = cacheKey(active.userId, clientId, role, page.url);
    const cached = readCached(entries, key, now());
    if (cached !== undefined) {
      return ok(cached);
    }
    try {
      return ok(
        await shared(key, async () => {
          const response = await api.interpret(active.token, {
            user_id: active.userId,
            client_id: clientId,
            role,
            action_context: { ...page, type: "page" },
          });
          if (reviewed(response)) {
            await remember(active, key, response);
          }
          return response;
        }),
      );
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) {
        await endSession();
        return SIGNED_OUT_REPLY;
      }
      return failed(error);
    }
  }

  async function interpret(page: PageContext): Promise<Result<InterpretResponse>> {
    const found = await context();
    return found === null ? SIGNED_OUT_REPLY : interpretIn(found, page);
  }

  async function report(detected: DetectedPage): Promise<boolean> {
    const found = await context();
    if (found === null || !found.settings.autoshow[detected.pageType]) {
      return false;
    }
    const reply = await interpretIn(found, detected.page);
    return reply.ok && !reply.value.silent && (reply.value.cards ?? []).length > 0 && reviewed(reply.value);
  }

  function handle(request: WorkerRequest) {
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
      case "page":
        return report(request.detected);
    }
  }

  return handle as Send;
}
