import { afterEach, describe, expect, it, vi } from "vitest";
import { ApiError, api, onUnauthorized } from "./client";

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

  it("reads a trace by its id", async () => {
    const fetchMock = respond(200, { id: "trace/1" });
    vi.stubGlobal("fetch", fetchMock);

    const trace = await api.trace("trace/1");

    expect(trace.id).toBe("trace/1");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/trace/trace%2F1");
    expect(init.method).toBe("GET");
    expect(init.credentials).toBe("include");
  });

  it("sends feedback on a card and expects no body back", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(api.feedback("card-1", false)).resolves.toBeUndefined();

    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/feedback");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ card_id: "card-1", useful: false });
  });

  it("raises ApiError when feedback is refused", async () => {
    vi.stubGlobal("fetch", respond(403, "foreign card"));

    const failure = await api.feedback("card-x", true).catch((error: unknown) => error);

    expect((failure as ApiError).status).toBe(403);
  });

  it("tells the subscriber when the session is gone", async () => {
    vi.stubGlobal("fetch", respond(401, "no session"));
    const expired = vi.fn();
    const unsubscribe = onUnauthorized(expired);

    const failure = await api.clients().catch((error: unknown) => error);
    unsubscribe();
    await api.clients().catch(() => undefined);

    expect((failure as ApiError).status).toBe(401);
    expect(expired).toHaveBeenCalledOnce();
  });

  it("raises ApiError with the response status", async () => {
    vi.stubGlobal("fetch", respond(404, "unknown user"));

    const failure = await api.authMock("nobody").catch((error: unknown) => error);

    expect(failure).toBeInstanceOf(ApiError);
    expect((failure as ApiError).status).toBe(404);
  });
});
