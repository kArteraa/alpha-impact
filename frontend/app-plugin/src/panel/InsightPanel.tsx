import "../styles/controls.css";
import "../styles/panel.css";
import type { ActionContext, InterpretResponse, Role } from "../types";
import { Card } from "./Card";
import { CheckIcon } from "./icons";

const SKELETON_LINES = 3;

export interface InsightPanelProps {
  actionContext: ActionContext;
  role: Role;
  response?: InterpretResponse;
  pending?: boolean;
  failed?: boolean;
  compact?: boolean;
  onRetry?: () => void;
  onFollowup?: (cardId: string) => void;
}

export function InsightPanel({
  actionContext,
  role,
  response,
  pending = false,
  failed = false,
  compact = false,
  onRetry,
  onFollowup,
}: InsightPanelProps) {
  const base = {
    className: compact ? "insight-panel insight-panel-compact" : "insight-panel",
    "data-action-type": actionContext.type,
    "data-role": role,
  };
  if (failed) {
    return (
      <section {...base} data-state="failed">
        <p className="panel-note">Не успел разобраться с этим действием</p>
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
        <p className="panel-note">Смотрю новости и позицию банка по этому действию</p>
      </section>
    );
  }
  const progress = pending && <div className="insight-progress" role="progressbar" aria-label="Обновляю вывод" />;
  if (response.silent) {
    return (
      <section {...base} data-state="silent" aria-busy={pending}>
        {progress}
        <p className="panel-silent" role="status">
          <CheckIcon />
          Ничего важного по этому действию
        </p>
        {response.silent_reason && <p className="panel-note">{response.silent_reason}</p>}
      </section>
    );
  }
  return (
    <section {...base} data-state="cards" aria-busy={pending}>
      {progress}
      {(response.cards ?? []).map((card) => (
        <Card key={card.id} card={card} compact={compact} onFollowup={onFollowup} />
      ))}
    </section>
  );
}
