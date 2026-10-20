import { ClaimTypeBadge, type InsightCard, Significance } from "@alpha-impact/plugin";

export function EventSummary({ event }: { event: InsightCard }) {
  const types = [...new Set(event.why_for_you.map((claim) => claim.type))];
  return (
    <li className="event">
      <div className="event-head">
        <h3>{event.headline}</h3>
        <Significance value={event.significance} />
      </div>
      <p className="muted">{event.why_for_you[0]?.text}</p>
      <div className="event-badges">
        {types.map((type) => (
          <ClaimTypeBadge key={type} type={type} />
        ))}
      </div>
    </li>
  );
}
