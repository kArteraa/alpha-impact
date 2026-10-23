import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useLoad } from "./useLoad";

describe("useLoad", () => {
  it("loads the value", async () => {
    const load = () => Promise.resolve("U_1941");
    const { result } = renderHook(() => useLoad(load));

    expect(result.current[0]).toEqual({ status: "loading" });
    await act(async () => {});

    expect(result.current[0]).toEqual({ status: "ready", value: "U_1941" });
  });

  it("does not show the previous value while a new loader runs", async () => {
    const first = () => Promise.resolve("U_1941");
    const second = () => new Promise<string>(() => {});
    const { result, rerender } = renderHook(({ load }) => useLoad(load), { initialProps: { load: first } });
    await act(async () => {});

    rerender({ load: second });

    expect(result.current[0]).toEqual({ status: "loading" });
  });

  it("reports a failed load", async () => {
    const failure = new Error("boom");
    const load = () => Promise.reject(failure);
    const { result } = renderHook(() => useLoad(load));

    await act(async () => {});

    expect(result.current[0]).toEqual({ status: "failed", error: failure });
  });
});
