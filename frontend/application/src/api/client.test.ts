import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api } from "./client";

function respond(status: number, body: unknown) {
  return vi.fn().mockResolvedValue(new Response(JSON.stringify(body), { status }));
}

describe("api client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("logs in with the session cookie included", async () => {
    const fetchMock = respond(200, { user_id: "user_cfo_wholesale" });
    vi.stubGlobal("fetch", fetchMock);

    const session = await api.authMock("user_cfo_wholesale");

    expect(session).toEqual({ user_id: "user_cfo_wholesale" });
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/auth/mock");
    expect(init.method).toBe("POST");
    expect(init.credentials).toBe("include");
    expect(JSON.parse(init.body)).toEqual({ user_id: "user_cfo_wholesale" });
  });

  it("raises ApiError with the response status", async () => {
    vi.stubGlobal("fetch", respond(404, "unknown user"));

    const failure = await api.authMock("nobody").catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(ApiError);
    expect((failure as ApiError).status).toBe(404);
  });
});
