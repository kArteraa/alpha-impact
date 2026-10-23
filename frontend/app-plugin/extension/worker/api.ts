import type { InterpretRequest, InterpretResponse } from "../../src";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

export class NetworkError extends Error {}

type Fetch = (url: string, init: RequestInit) => Promise<Response>;

export type ExtensionApi = ReturnType<typeof createApi>;

const JSON_BODY = { "Content-Type": "application/json" };

export function createApi(base: string, fetch: Fetch) {
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
    authMock: (userId: string) =>
      request<{ user_id: string }>("/auth/mock", {
        method: "POST",
        credentials: "include",
        headers: JSON_BODY,
        body: JSON.stringify({ user_id: userId }),
      }),
    extensionToken: () =>
      request<{ token: string; expires_at: string }>("/auth/extension-token", {
        method: "POST",
        credentials: "include",
      }),
    clients: () => request<string[]>("/clients", { method: "GET", credentials: "include" }),
    interpret: (token: string, body: InterpretRequest) =>
      request<InterpretResponse>("/interpret", {
        method: "POST",
        credentials: "omit",
        headers: { ...JSON_BODY, Authorization: `Bearer ${token}` },
        body: JSON.stringify(body),
      }),
  };
}
