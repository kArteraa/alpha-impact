import { useEffect, useState } from "react";

export type Load<T> = { status: "loading" } | { status: "failed"; error: unknown } | { status: "ready"; value: T };

interface Loaded<T> {
  load: () => Promise<T>;
  result: Load<T>;
}

export function useLoad<T>(load: () => Promise<T>): [Load<T>, (value: T) => void] {
  const [loaded, setLoaded] = useState<Loaded<T> | null>(null);

  useEffect(() => {
    let active = true;
    const settle = (result: Load<T>) => {
      if (active) {
        setLoaded({ load, result });
      }
    };
    load().then(
      (value) => settle({ status: "ready", value }),
      (error: unknown) => settle({ status: "failed", error }),
    );
    return () => {
      active = false;
    };
  }, [load]);

  const result: Load<T> = loaded?.load === load ? loaded.result : { status: "loading" };
  return [result, (value) => setLoaded({ load, result: { status: "ready", value } })];
}
