import { type ActionContext, useInterpret } from "@alpha-impact/plugin";
import type { ReactNode } from "react";
import { useSession } from "../session/context";
import { Panel } from "./Panel";
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
    <Panel
      actionContext={context}
      role={role}
      response={insight.response}
      pending={insight.pending}
      failed={insight.failed}
      onRetry={insight.retry}
    />
  );
}
