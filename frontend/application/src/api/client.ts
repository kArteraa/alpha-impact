import type { ClientProfile, Feature, InterpretRequest, InterpretResponse } from "@alpha-impact/plugin";

const API_BASE = "/api";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!response.ok) {
    throw new ApiError(response.status, await response.text());
  }
  return (await response.json()) as T;
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
};
