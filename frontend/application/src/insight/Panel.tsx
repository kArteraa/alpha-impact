import { InsightPanel, type InsightPanelProps } from "@alpha-impact/plugin";
import { API_BASE, api } from "../api/client";

export function Panel(props: Omit<InsightPanelProps, "apiBase" | "onFeedback">) {
  return <InsightPanel {...props} apiBase={API_BASE} onFeedback={api.feedback} />;
}
