import type { InterpretRequest, InterpretResponse } from "../../src";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export class NetworkError extends Error {}

export interface ExtensionToken {
  token: string;
  expires_at: string;
}

export interface ExtensionApi {
  authMock(userId: string): Promise<{ user_id: string }>;
  extensionToken(): Promise<ExtensionToken>;
  clients(): Promise<string[]>;
  interpret(token: string, body: InterpretRequest): Promise<InterpretResponse>;
}

type Fetch = (url: string, init: RequestInit) => Promise<Response>;

const JSON_BODY = { "Content-Type": "application/json" };

export function createApi(base: string, fetch: Fetch): ExtensionApi {
  async function request<T>(path: string, init: RequestInit): Promise<T> {
    let response: Response;
    try {
      response = await fetch(`${base}${path}`, init);
    } catch (error) {
      throw new NetworkError(String(error));
    }
    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }
    return (await response.json()) as T;
  }

  return {
    authMock: (userId) =>
      request("/auth/mock", {
        method: "POST",
        credentials: "include",
        headers: JSON_BODY,
        body: JSON.stringify({ user_id: userId }),
      }),
    extensionToken: () => request("/auth/extension-token", { method: "POST", credentials: "include" }),
    clients: () => request("/clients", { method: "GET", credentials: "include" }),
    interpret: (token, body) =>
      request("/interpret", {
        method: "POST",
        credentials: "omit",
        headers: { ...JSON_BODY, Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      }),
  };
}
