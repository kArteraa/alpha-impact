import type { InsightCard } from "@alpha-impact/plugin";
import type { ReactNode } from "react";
import { useFeed } from "../feed/context";

const SKELETON_LINES = 3;

interface FeedStatusProps {
  empty: ReactNode;
  children: (cards: InsightCard[]) => ReactNode;
}

export function FeedStatus({ empty, children }: FeedStatusProps) {
  const { response, failed, retry } = useFeed();
  if (failed) {
    return (
      <div className="feed-status" data-state="failed">
        <p className="empty">Не успел собрать события</p>
        <button type="button" className="button-secondary" onClick={retry}>
          Попробовать ещё раз
        </button>
      </div>
    );
  }
  if (response === undefined) {
    return (
      <div className="feed-status" data-state="checking" aria-busy="true">
        {Array.from({ length: SKELETON_LINES }, (_, index) => (
          <span key={index} className="insight-skeleton" />
        ))}
        <p className="empty">Смотрю новости и позицию банка за 14 дней</p>
      </div>
    );
  }
  const cards = response.cards ?? [];
  if (response.silent || cards.length === 0) {
    return (
      <div className="feed-status" data-state="silent" role="status">
        {empty}
      </div>
    );
  }
  return children(cards);
}
