import { useEffect, useState } from "react";

export type Load<T> = { status: "loading" } | { status: "failed"; error: unknown } | { status: "ready"; value: T };

export function useLoad<T>(load: () => Promise<T>): [Load<T>, (value: T) => void] {
  const [state, setState] = useState<Load<T>>({ status: "loading" });

  useEffect(() => {
    let active = true;
    load().then(
      (value) => {
        if (active) {
          setState({ status: "ready", value });
        }
      },
      (error: unknown) => {
        if (active) {
          setState({ status: "failed", error });
        }
      },
    );
    return () => {
      active = false;
    };
  }, [load]);

  return [state, (value) => setState({ status: "ready", value })];
}
