import type { InsightCard } from "@alpha-impact/plugin";
import type { ReactNode } from "react";
import { useFeed } from "../feed/context";
import { Skeleton } from "../ui/Skeleton";

interface FeedStatusProps {
  empty: ReactNode;
  children: (cards: InsightCard[]) => ReactNode;
}

export function FeedStatus({ empty, children }: FeedStatusProps) {
  const { response, pending, failed, retry } = useFeed();
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
        <Skeleton text="Смотрю новости и позицию банка" />
      </div>
    );
  }
  const cards = response.cards ?? [];
  return (
    <div className="feed-current">
      {pending && <div className="insight-progress" role="progressbar" aria-label="Обновляю ленту" />}
      {response.silent || cards.length === 0 ? (
        <div className="feed-status" data-state="silent" role="status">
          {empty}
        </div>
      ) : (
        children(cards)
      )}
    </div>
  );
}
