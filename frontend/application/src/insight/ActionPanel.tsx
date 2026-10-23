import { type ActionContext, InsightPanel, useInterpret } from "@alpha-impact/plugin";
import type { ReactNode } from "react";
import { API_BASE, api } from "../api/client";
import { useSession } from "../session/context";
import { useInterpretFetcher } from "./useInterpretFetcher";

interface ActionPanelProps {
  context: ActionContext | null;
  placeholder: ReactNode;
}

export function ActionPanel({ context, placeholder }: ActionPanelProps) {
  const { role } = useSession();
  const insight = useInterpret(context, useInterpretFetcher());
  if (context === null) {
    return <>{placeholder}</>;
  }
  return (
    <InsightPanel
      actionContext={context}
      role={role}
      response={insight.response}
      pending={insight.pending}
      failed={insight.failed}
      onRetry={insight.retry}
      apiBase={API_BASE}
      onFeedback={api.feedback}
    />
  );
}
