import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mockResponses } from "./mocks";
import type { ActionContext, InterpretResponse } from "./types";
import { INTERPRET_DELAY_MS, type InterpretFetcher, useInterpret } from "./useInterpret";

const first: ActionContext = { type: "payment", amount: 1500, beneficiary_id: "cp_logistics_spb" };
const second: ActionContext = { type: "payment", amount: 2500, beneficiary_id: "cp_logistics_spb" };

function deferred() {
  let resolve: (value: InterpretResponse) => void = () => {};
  let reject: (reason: unknown) => void = () => {};
  const promise = new Promise<InterpretResponse>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

async function flush() {
  await act(async () => {
    await Promise.resolve();
  });
}

describe("useInterpret", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("asks only after the delay and returns the response", async () => {
    const fetcher = vi.fn<InterpretFetcher>().mockResolvedValue(mockResponses.cards);
    const { result } = renderHook(() => useInterpret(first, fetcher));

    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS - 1));
    expect(fetcher).not.toHaveBeenCalled();
    expect(result.current.pending).toBe(true);

    act(() => vi.advanceTimersByTime(1));
    await flush();

    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][0]).toEqual(first);
    expect(result.current.response).toBe(mockResponses.cards);
    expect(result.current.pending).toBe(false);
  });

  it("sends only the latest context when it changes within the delay", async () => {
    const fetcher = vi.fn<InterpretFetcher>().mockResolvedValue(mockResponses.cards);
    const { rerender } = renderHook(({ context }) => useInterpret(context, fetcher), {
      initialProps: { context: first },
    });

    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS / 2));
    rerender({ context: second });
    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS));
    await flush();

    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(fetcher.mock.calls[0][0]).toEqual(second);
  });

  it("aborts the previous request and keeps the old response until the new one arrives", async () => {
    const later = deferred();
    const fetcher = vi
      .fn<InterpretFetcher>()
      .mockResolvedValueOnce(mockResponses.cards)
      .mockReturnValueOnce(later.promise)
      .mockResolvedValueOnce(mockResponses.silent);
    const { result, rerender } = renderHook(({ context }) => useInterpret(context, fetcher), {
      initialProps: { context: first },
    });
    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS));
    await flush();

    rerender({ context: second });
    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS));
    expect(result.current.response).toBe(mockResponses.cards);
    expect(result.current.pending).toBe(true);

    rerender({ context: first });
    expect(fetcher.mock.calls[1][1].aborted).toBe(true);
    later.resolve(mockResponses.updated);
    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS));
    await flush();

    expect(result.current.response).toBe(mockResponses.silent);
  });

  it("reports a failure and asks again on retry", async () => {
    const fetcher = vi
      .fn<InterpretFetcher>()
      .mockRejectedValueOnce(new Error("timeout"))
      .mockResolvedValueOnce(mockResponses.cards);
    const { result } = renderHook(() => useInterpret(first, fetcher));
    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS));
    await flush();

    expect(result.current.failed).toBe(true);
    expect(result.current.pending).toBe(false);

    act(() => result.current.retry());
    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS));
    await flush();

    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(result.current.failed).toBe(false);
    expect(result.current.response).toBe(mockResponses.cards);
  });

  it("does not restart the delay when the fetcher is a new function on every render", async () => {
    const answerWith = vi.fn().mockResolvedValue(mockResponses.cards);
    const { rerender } = renderHook(() => useInterpret(first, (context, signal) => answerWith(context, signal)));

    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS / 2));
    rerender();
    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS / 2));
    await flush();

    expect(answerWith).toHaveBeenCalledTimes(1);
  });

  it("does not reuse an old result when the context comes back to it", async () => {
    const fetcher = vi
      .fn<InterpretFetcher>()
      .mockRejectedValueOnce(new Error("timeout"))
      .mockReturnValue(new Promise<InterpretResponse>(() => {}));
    const { result, rerender } = renderHook(({ context }) => useInterpret(context, fetcher), {
      initialProps: { context: first },
    });
    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS));
    await flush();
    expect(result.current.failed).toBe(true);

    rerender({ context: second });
    rerender({ context: first });

    expect(result.current.failed).toBe(false);
    expect(result.current.pending).toBe(true);
  });

  it("does not ask without a context and keeps the last response", async () => {
    const fetcher = vi.fn<InterpretFetcher>().mockResolvedValue(mockResponses.cards);
    const { result, rerender } = renderHook(({ context }) => useInterpret(context, fetcher), {
      initialProps: { context: first as ActionContext | null },
    });
    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS));
    await flush();

    rerender({ context: null });
    act(() => vi.advanceTimersByTime(INTERPRET_DELAY_MS * 2));
    await flush();

    expect(fetcher).toHaveBeenCalledTimes(1);
    expect(result.current.response).toBe(mockResponses.cards);
    expect(result.current.pending).toBe(false);
  });
});
