import type { ActionContext, Claim, InsightCard, InterpretResponse, Role, SourceRef } from "./types";

export interface InsightPanelProps {
  actionContext: ActionContext;
  role: Role;
  response?: InterpretResponse;
}

const CLAIM_LABELS: Record<Claim["type"], string> = {
  fact: "факт",
  bank: "позиция банка",
  ai: "вывод AI",
};

const BLOCKS = [
  ["what_happened", "Что произошло"],
  ["why_for_you", "Почему это важно для вас"],
  ["consequences", "Последствия"],
  ["actions", "Действия"],
  ["bank_view", "Как это оценивает банк"],
] as const;

function Source({ source }: { source: SourceRef }) {
  const label = source.title ?? source.id;
  if (source.url) {
    return (
      <a href={source.url} target="_blank" rel="noreferrer">
        {label}
      </a>
    );
  }
  return <span>{label}</span>;
}

function ClaimItem({ claim }: { claim: Claim }) {
  return (
    <li>
      {claim.text}
      <span className="claim-type" data-claim-type={claim.type}>
        {CLAIM_LABELS[claim.type]}
      </span>
      {" · "}
      <Source source={claim.source_ref} />
    </li>
  );
}

function Card({ card }: { card: InsightCard }) {
  return (
    <article className="insight-card" data-significance={card.significance}>
      <h2>{card.headline}</h2>
      {BLOCKS.map(([key, title]) => (
        <section key={key}>
          <h3>{title}</h3>
          <ul>
            {card[key].map((claim, index) => (
              <ClaimItem key={index} claim={claim} />
            ))}
          </ul>
        </section>
      ))}
      {card.product_offer && (
        <section className="product-offer">
          <h3>Продукт банка</h3>
          <p>
            <strong>{card.product_offer.product}</strong>: {card.product_offer.reason}
          </p>
        </section>
      )}
      <section>
        <h3>На чём основан вывод</h3>
        <ul>
          {card.basis.map((source) => (
            <li key={source.id}>
              <Source source={source} />
            </li>
          ))}
        </ul>
      </section>
      {card.needs_review && <p className="needs-review">Карточка ждёт проверки</p>}
      <a className="trace-link" href={`/trace/${card.trace_id}`}>
        Как получен вывод
      </a>
    </article>
  );
}

export function InsightPanel({ actionContext, role, response }: InsightPanelProps) {
  const base = {
    className: "insight-panel",
    "data-action-type": actionContext.type,
    "data-role": role,
  };
  if (response === undefined) {
    return (
      <section {...base} data-state="checking" aria-busy="true">
        <p>Проверяю, что изменилось вокруг этого действия…</p>
      </section>
    );
  }
  if (response.silent) {
    return (
      <section {...base} data-state="silent">
        <p>По этому действию ничего важного.</p>
        {response.silent_reason && <p className="silent-reason">{response.silent_reason}</p>}
      </section>
    );
  }
  return (
    <section {...base} data-state="cards">
      {(response.cards ?? []).map((card) => (
        <Card key={card.id} card={card} />
      ))}
    </section>
  );
}
