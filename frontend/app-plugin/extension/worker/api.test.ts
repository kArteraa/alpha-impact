import { describe, expect, it, vi } from "vitest";
import { mockResponses } from "../../src/mocks";
import { ApiError, NetworkError, createApi } from "./api";

const BASE = "http://api.test";

function replying(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status }));
}

function sent(fetch: ReturnType<typeof vi.fn>) {
  const [url, init] = fetch.mock.calls[0] as [string, RequestInit];
  return { url, init, headers: new Headers(init.headers) };
}

describe("extension api", () => {
  it("signs in with the mock session cookie", async () => {
    const fetch = replying(200, { user_id: "user_cfo" });

    await expect(createApi(BASE, fetch).authMock("user_cfo")).resolves.toEqual({ user_id: "user_cfo" });

    const { url, init } = sent(fetch);
    expect(url).toBe(`${BASE}/auth/mock`);
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body as string)).toEqual({ user_id: "user_cfo" });
  });

  it("trades the session cookie for an extension token", async () => {
    const token = { token: "t-1", expires_at: "2026-10-23T13:00:00Z" };
    const fetch = replying(200, token);

    await expect(createApi(BASE, fetch).extensionToken()).resolves.toEqual(token);

    const { url, init } = sent(fetch);
    expect(url).toBe(`${BASE}/auth/extension-token`);
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
  });

  it("lists clients by the session cookie", async () => {
    const fetch = replying(200, ["U_1941"]);

    await expect(createApi(BASE, fetch).clients()).resolves.toEqual(["U_1941"]);

    const { url, init } = sent(fetch);
    expect(url).toBe(`${BASE}/clients`);
    expect(init.credentials).toBe("include");
  });

  it("sends interpret with the bearer token and without cookies", async () => {
    const fetch = replying(200, mockResponses.cards);
    const body = {
      user_id: "user_cfo",
      client_id: "U_1941",
      role: "cfo",
      action_context: { type: "page", url: "https://news.test/a", text: "Ставка" },
    } as const;

    await expect(createApi(BASE, fetch).interpret("t-1", body)).resolves.toEqual(mockResponses.cards);

    const { url, init, headers } = sent(fetch);
    expect(url).toBe(`${BASE}/interpret`);
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("omit");
    expect(headers.get("Authorization")).toBe("Bearer t-1");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(JSON.parse(init.body as string)).toEqual(body);
  });

  it("turns a failed status into an ApiError with that status", async () => {
    const failure = await createApi(BASE, replying(501, { detail: "Not implemented" }))
      .extensionToken()
      .catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(ApiError);
    expect((failure as ApiError).status).toBe(501);
  });

  it("turns an unreachable server into a NetworkError", async () => {
    const fetch = vi.fn(async () => {
      throw new TypeError("Failed to fetch");
    });

    await expect(createApi(BASE, fetch).clients()).rejects.toBeInstanceOf(NetworkError);
  });
});
