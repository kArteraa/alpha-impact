import { type ActionContext, InsightPanel, type InterpretFetcher, useInterpret } from "@alpha-impact/plugin";
import type { ReactNode } from "react";
import { api } from "../api/client";
import { useCompany } from "../company/context";
import { useSession } from "../session/context";

interface ActionPanelProps {
  context: ActionContext | null;
  placeholder: ReactNode;
}

export function ActionPanel({ context, placeholder }: ActionPanelProps) {
  const { company } = useCompany();
  const { userId, role } = useSession();
  const interpret: InterpretFetcher = (action, signal) =>
    api.interpret({ user_id: userId, client_id: company.id, role, action_context: action }, signal);
  const insight = useInterpret(context, interpret);
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
    />
  );
}
