import "../styles/controls.css";
import "../styles/panel.css";
import type { ActionContext, InterpretResponse, Role } from "../types";
import { ApiBaseContext } from "./apiBase";
import { Card } from "./Card";
import type { FeedbackHandler } from "./CardFooter";
import { CheckIcon } from "./icons";

const SKELETON_LINES = 3;

export interface PanelNotes {
  pending: string;
  failed: string;
  silent: string;
}

const ACTION_NOTES: PanelNotes = {
  pending: "Смотрю новости и позицию банка по этому действию",
  failed: "Не успел разобраться с этим действием",
  silent: "Ничего важного по этому действию",
};

export interface InsightPanelProps {
  actionContext: ActionContext;
  role: Role;
  response?: InterpretResponse;
  pending?: boolean;
  failed?: boolean;
  compact?: boolean;
  notes?: PanelNotes;
  onRetry?: () => void;
  onFollowup?: (cardId: string) => void;
  onFeedback?: FeedbackHandler;
  apiBase?: string;
}

export function InsightPanel({
  actionContext,
  role,
  response,
  pending = false,
  failed = false,
  compact = false,
  notes = ACTION_NOTES,
  onRetry,
  onFollowup,
  onFeedback,
  apiBase,
}: InsightPanelProps) {
  const base = {
    className: compact ? "insight-panel insight-panel-compact" : "insight-panel",
    "data-action-type": actionContext.type,
    "data-role": role,
  };
  if (failed) {
    return (
      <section {...base} data-state="failed">
        <p className="panel-note">{notes.failed}</p>
        {onRetry && (
          <button type="button" className="button-secondary" onClick={onRetry}>
            Попробовать ещё раз
          </button>
        )}
      </section>
    );
  }
  if (response === undefined) {
    return (
      <section {...base} data-state="checking" aria-busy="true">
        {Array.from({ length: SKELETON_LINES }, (_, index) => (
          <span key={index} className="insight-skeleton" />
        ))}
        <p className="panel-note">{notes.pending}</p>
      </section>
    );
  }
  const progress = pending && <div className="insight-progress" role="progressbar" aria-label="Обновляю вывод" />;
  const cards = response.cards ?? [];
  if (response.silent || cards.length === 0) {
    return (
      <section {...base} data-state="silent" aria-busy={pending}>
        {progress}
        <p className="panel-silent" role="status">
          <CheckIcon />
          {notes.silent}
        </p>
        {response.silent_reason && <p className="panel-note">{response.silent_reason}</p>}
      </section>
    );
  }
  return (
    <section {...base} data-state="cards" aria-busy={pending}>
      {progress}
      <ApiBaseContext.Provider value={apiBase}>
        {cards.map((card) => (
          <Card key={card.id} card={card} compact={compact} onFollowup={onFollowup} onFeedback={onFeedback} />
        ))}
      </ApiBaseContext.Provider>
    </section>
  );
}
