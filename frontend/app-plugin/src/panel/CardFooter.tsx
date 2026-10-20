import { useState } from "react";
import { ThumbDownIcon, ThumbUpIcon } from "./icons";

type Feedback = "useful" | "useless" | null;

interface CardFooterProps {
  cardId: string;
  traceId: string;
  onFollowup?: (cardId: string) => void;
}

export function CardFooter({ cardId, traceId, onFollowup }: CardFooterProps) {
  const [feedback, setFeedback] = useState<Feedback>(null);
  const toggle = (value: Exclude<Feedback, null>) => setFeedback((current) => (current === value ? null : value));
  return (
    <footer className="card-footer">
      <a className="trace-link" href={`/trace/${traceId}`}>
        Как получен вывод
      </a>
      <span className="feedback">
        <button
          type="button"
          className="icon-button"
          aria-label="Полезно"
          aria-pressed={feedback === "useful"}
          onClick={() => toggle("useful")}
        >
          <ThumbUpIcon />
        </button>
        <button
          type="button"
          className="icon-button"
          aria-label="Не полезно"
          aria-pressed={feedback === "useless"}
          onClick={() => toggle("useless")}
        >
          <ThumbDownIcon />
        </button>
      </span>
      {onFollowup && (
        <button type="button" className="button-ghost" onClick={() => onFollowup(cardId)}>
          Задать вопрос
        </button>
      )}
    </footer>
  );
}
