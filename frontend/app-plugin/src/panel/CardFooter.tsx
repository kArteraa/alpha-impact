import { useState } from "react";
import { ThumbDownIcon, ThumbUpIcon } from "./icons";

export type FeedbackHandler = (cardId: string, useful: boolean) => Promise<void>;

const FEEDBACK = [
  { useful: true, label: "Полезно", Icon: ThumbUpIcon },
  { useful: false, label: "Не полезно", Icon: ThumbDownIcon },
] as const;

interface CardFooterProps {
  cardId: string;
  traceId: string;
  onFollowup?: (cardId: string) => void;
  onFeedback?: FeedbackHandler;
}

function Feedback({ cardId, onFeedback }: { cardId: string; onFeedback: FeedbackHandler }) {
  const [chosen, setChosen] = useState<boolean | null>(null);
  const [status, setStatus] = useState<"idle" | "sending" | "failed">("idle");

  async function send(useful: boolean) {
    if (useful === chosen) {
      return;
    }
    setStatus("sending");
    try {
      await onFeedback(cardId, useful);
      setChosen(useful);
      setStatus("idle");
    } catch {
      setStatus("failed");
    }
  }

  return (
    <span className="insight-feedback">
      {status === "failed" && (
        <span className="feedback-note" role="status">
          Отзыв не отправлен
        </span>
      )}
      {FEEDBACK.map(({ useful, label, Icon }) => (
        <button
          key={label}
          type="button"
          className="icon-button"
          aria-label={label}
          aria-pressed={chosen === useful}
          disabled={status === "sending"}
          onClick={() => void send(useful)}
        >
          <Icon />
        </button>
      ))}
    </span>
  );
}

export function CardFooter({ cardId, traceId, onFollowup, onFeedback }: CardFooterProps) {
  return (
    <footer className="card-footer">
      <a className="trace-link" href={`/trace/${traceId}`}>
        Как получен вывод
      </a>
      {onFeedback && <Feedback cardId={cardId} onFeedback={onFeedback} />}
      {onFollowup && (
        <button type="button" className="button-ghost" onClick={() => onFollowup(cardId)}>
          Задать вопрос
        </button>
      )}
    </footer>
  );
}
