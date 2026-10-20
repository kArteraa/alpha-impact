import { useState } from "react";
import { ThumbDownIcon, ThumbUpIcon } from "./icons";

type Feedback = "useful" | "useless";

const FEEDBACK = [
  { value: "useful", label: "Полезно", Icon: ThumbUpIcon },
  { value: "useless", label: "Не полезно", Icon: ThumbDownIcon },
] as const;

interface CardFooterProps {
  cardId: string;
  traceId: string;
  onFollowup?: (cardId: string) => void;
}

export function CardFooter({ cardId, traceId, onFollowup }: CardFooterProps) {
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  return (
    <footer className="card-footer">
      <a className="trace-link" href={`/trace/${traceId}`}>
        Как получен вывод
      </a>
      <span className="insight-feedback">
        {FEEDBACK.map(({ value, label, Icon }) => (
          <button
            key={value}
            type="button"
            className="icon-button"
            aria-label={label}
            aria-pressed={feedback === value}
            onClick={() => setFeedback((current) => (current === value ? null : value))}
          >
            <Icon />
          </button>
        ))}
      </span>
      {onFollowup && (
        <button type="button" className="button-ghost" onClick={() => onFollowup(cardId)}>
          Задать вопрос
        </button>
      )}
    </footer>
  );
}
