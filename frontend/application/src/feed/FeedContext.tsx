import { useInterpret } from "@alpha-impact/plugin";
import type { ReactNode } from "react";
import { useInterpretFetcher } from "../insight/useInterpretFetcher";
import { DASHBOARD, FeedContext } from "./context";

export function FeedProvider({ children }: { children: ReactNode }) {
  const feed = useInterpret(DASHBOARD, useInterpretFetcher());
  return <FeedContext.Provider value={feed}>{children}</FeedContext.Provider>;
}
