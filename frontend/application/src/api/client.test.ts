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

  it("reads the client profile", async () => {
    const fetchMock = respond(200, { client_id: "U_1941" });
    vi.stubGlobal("fetch", fetchMock);

    const profile = await api.profile("U_1941");

    expect(profile.client_id).toBe("U_1941");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/profile/U_1941");
    expect(init.method).toBe("GET");
  });

  it("corrects a profile feature with PATCH", async () => {
    const fetchMock = respond(200, { client_id: "U_1941" });
    vi.stubGlobal("fetch", fetchMock);

    await api.patchFeature("U_1941", "industry_class", "logistics");

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/profile/U_1941/features/industry_class");
    expect(init.method).toBe("PATCH");
    expect(JSON.parse(init.body)).toEqual({ value: "logistics" });
  });

  it("passes the abort signal to the interpret request", async () => {
    const fetchMock = respond(200, { silent: true, cards: [] });
    vi.stubGlobal("fetch", fetchMock);
    const controller = new AbortController();
    const body = {
      user_id: "user_cfo_wholesale",
      client_id: "U_1941",
      role: "cfo" as const,
      action_context: { type: "payment" as const, amount: 1000, beneficiary_id: "U_96105" },
    };

    await api.interpret(body, controller.signal);

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/interpret");
    expect(init.signal).toBe(controller.signal);
    expect(JSON.parse(init.body)).toEqual(body);
  });

  it("raises ApiError with the response status", async () => {
    vi.stubGlobal("fetch", respond(404, "unknown user"));

    const failure = await api.authMock("nobody").catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(ApiError);
    expect((failure as ApiError).status).toBe(404);
  });
});
