import { type ActionContext, type InsightPanelProps, useInterpret } from "@alpha-impact/plugin";
import type { ReactNode } from "react";
import { useSession } from "../session/context";
import { Panel } from "./Panel";
import { useInterpretFetcher } from "./useInterpretFetcher";

interface ActionPanelProps extends Pick<InsightPanelProps, "notes"> {
  context: ActionContext | null;
  placeholder: ReactNode;
}

export function ActionPanel({ context, placeholder, notes }: ActionPanelProps) {
  const { role } = useSession();
  const insight = useInterpret(context, useInterpretFetcher());
  if (context === null) {
    return <>{placeholder}</>;
  }
  return (
    <Panel
      actionContext={context}
      role={role}
      response={insight.response}
      pending={insight.pending}
      failed={insight.failed}
      notes={notes}
      onRetry={insight.retry}
    />
  );
}
