import type { ClientProfile, Feature, InterpretRequest, InterpretResponse, Trace } from "@alpha-impact/plugin";

export const API_BASE = "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

const unauthorizedHandlers = new Set<() => void>();

export function onUnauthorized(handler: () => void): () => void {
  unauthorizedHandlers.add(handler);
  return () => {
    unauthorizedHandlers.delete(handler);
  };
}

async function send(path: string, init: RequestInit): Promise<Response> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (response.status === 401) {
    unauthorizedHandlers.forEach((handler) => handler());
  }
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
  return response;
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  return (await (await send(path, init)).json()) as T;
}

export const api = {
  authMock: (userId: string) =>
    request<{ user_id: string }>("/auth/mock", {
      method: "POST",
      body: JSON.stringify({ user_id: userId }),
    }),
  clients: () => request<string[]>("/clients", { method: "GET" }),
  profile: (clientId: string) => request<ClientProfile>(`/profile/${clientId}`, { method: "GET" }),
  patchFeature: (clientId: string, name: string, value: Feature["value"]) =>
    request<ClientProfile>(`/profile/${clientId}/features/${name}`, {
      method: "PATCH",
      body: JSON.stringify({ value }),
    }),
  interpret: (body: InterpretRequest, signal?: AbortSignal) =>
    request<InterpretResponse>("/interpret", { method: "POST", body: JSON.stringify(body), signal }),
  trace: (traceId: string) => request<Trace>(`/trace/${encodeURIComponent(traceId)}`, { method: "GET" }),
  feedback: async (cardId: string, useful: boolean) => {
    await send("/feedback", { method: "POST", body: JSON.stringify({ card_id: cardId, useful }) });
  },
};
