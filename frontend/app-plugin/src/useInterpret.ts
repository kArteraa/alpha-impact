import { useEffect, useState } from "react";
import type { ActionContext, InterpretResponse } from "./types";

export const INTERPRET_DELAY_MS = 500;

export type InterpretFetcher = (context: ActionContext, signal: AbortSignal) => Promise<InterpretResponse>;

export interface InterpretState {
  response?: InterpretResponse;
  pending: boolean;
  failed: boolean;
  retry: () => void;
}

interface Settled {
  key: string;
  attempt: number;
  failed: boolean;
}

export function useInterpret(context: ActionContext | null, fetcher: InterpretFetcher): InterpretState {
  const key = context === null ? null : JSON.stringify(context);
  const [response, setResponse] = useState<InterpretResponse>();
  const [settled, setSettled] = useState<Settled | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    if (key === null) {
      return;
    }
    const controller = new AbortController();
    const settle = (failed: boolean) => setSettled({ key, attempt, failed });
    const timer = setTimeout(() => {
      fetcher(JSON.parse(key) as ActionContext, controller.signal).then(
        (next) => {
          if (!controller.signal.aborted) {
            setResponse(next);
            settle(false);
          }
        },
        () => {
          if (!controller.signal.aborted) {
            settle(true);
          }
        },
      );
    }, INTERPRET_DELAY_MS);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [key, attempt, fetcher]);

  const current = key !== null && settled?.key === key && settled.attempt === attempt;
  return {
    response,
    pending: key !== null && !current,
    failed: current && settled.failed,
    retry: () => setAttempt((value) => value + 1),
  };
}
