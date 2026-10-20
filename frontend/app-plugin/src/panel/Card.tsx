import type { InsightCard } from "../types";
import { Block } from "./Block";
import { CardFooter } from "./CardFooter";
import { ClaimList } from "./ClaimList";
import { formatDate, sourceTitle } from "./labels";
import { ProductOffer } from "./ProductOffer";
import { Significance } from "./Significance";
import { SourceList } from "./SourceList";

interface CardProps {
  card: InsightCard;
  compact: boolean;
  onFollowup?: (cardId: string) => void;
}

function BankReport({ card }: { card: InsightCard }) {
  const report = card.bank_view[0]?.source_ref;
  if (!report) {
    return null;
  }
  return (
    <p className="bank-report">
      {report.published_at && <>Отчёт от {formatDate(report.published_at)} · </>}
      {report.url ? (
        <a href={report.url} target="_blank" rel="noreferrer">
          {sourceTitle(report)}
        </a>
      ) : (
        sourceTitle(report)
      )}
    </p>
  );
}

export function Card({ card, compact, onFollowup }: CardProps) {
  return (
    <div className="insight-item">
      <article className="insight-card" data-significance={card.significance}>
        <header className="card-header">
          <h3>{card.headline}</h3>
          <Significance value={card.significance} />
        </header>
        <Block title="Почему это важно для вас" collapsible={false} className="block-why">
          <ClaimList claims={card.why_for_you} withTraits />
        </Block>
        <Block title="Что произошло" collapsible>
          <ClaimList claims={card.what_happened} />
        </Block>
        <Block title="Последствия" collapsible={compact}>
          <ClaimList claims={card.consequences} />
        </Block>
        <Block title="Что можно сделать" collapsible={compact}>
          <ClaimList claims={card.actions} />
        </Block>
        <Block title="Как это оценивает банк" collapsible={compact} className="block-bank">
          <ClaimList claims={card.bank_view} />
          <BankReport card={card} />
        </Block>
        <Block title="На чём основан вывод" collapsible={compact}>
          <SourceList sources={card.basis} />
        </Block>
        {card.needs_review && <p className="needs-review">Карточка ждёт проверки</p>}
      </article>
      {card.product_offer && <ProductOffer offer={card.product_offer} />}
      <CardFooter cardId={card.id} traceId={card.trace_id} onFollowup={onFollowup} />
    </div>
  );
}
