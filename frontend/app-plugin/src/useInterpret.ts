import { useCallback, useEffect, useRef, useState } from "react";
import type { ActionContext, InterpretResponse } from "./types";

export const INTERPRET_DELAY_MS = 500;

export type InterpretFetcher = (context: ActionContext, signal: AbortSignal) => Promise<InterpretResponse>;

export interface InterpretState {
  response?: InterpretResponse;
  pending: boolean;
  failed: boolean;
  retry: () => void;
}

interface Run {
  key: string | null;
  attempt: number;
  id: number;
}

interface Settled {
  id: number;
  failed: boolean;
}

export function useInterpret(context: ActionContext | null, fetcher: InterpretFetcher): InterpretState {
  const key = context === null ? null : JSON.stringify(context);
  const [response, setResponse] = useState<InterpretResponse>();
  const [settled, setSettled] = useState<Settled | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [run, setRun] = useState<Run>({ key, attempt, id: 0 });
  const fetcherRef = useRef(fetcher);

  if (run.key !== key || run.attempt !== attempt) {
    setRun({ key, attempt, id: run.id + 1 });
  }

  useEffect(() => {
    fetcherRef.current = fetcher;
  }, [fetcher]);

  useEffect(() => {
    if (run.key === null) {
      return;
    }
    const controller = new AbortController();
    const settle = (failed: boolean) => setSettled({ id: run.id, failed });
    const runContext = JSON.parse(run.key) as ActionContext;
    const timer = setTimeout(() => {
      fetcherRef.current(runContext, controller.signal).then(
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
  }, [run]);

  const retry = useCallback(() => setAttempt((value) => value + 1), []);
  const current = key !== null && settled?.id === run.id;
  return { response, pending: key !== null && !current, failed: current && settled.failed, retry };
}
