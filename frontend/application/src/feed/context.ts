import type { DashboardContext, InterpretState } from "@alpha-impact/plugin";
import { createContext, useContext } from "react";

export const DASHBOARD: DashboardContext = { type: "dashboard" };

export const FeedContext = createContext<InterpretState | null>(null);

export function useFeed(): InterpretState {
  const value = useContext(FeedContext);
  if (value === null) {
    throw new Error("useFeed must be used inside FeedProvider");
  }
  return value;
}
