import { ClaimTypeBadge, type InsightCard, Significance } from "@alpha-impact/plugin";
import { Link } from "react-router";

export function EventSummary({ event }: { event: InsightCard }) {
  const consequence = event.consequences[0];
  const types = [...new Set(event.consequences.map((claim) => claim.type))];
  return (
    <li className="event">
      <div className="event-head">
        <h3>
          <Link to={`/events/${event.id}`}>{event.headline}</Link>
        </h3>
        <Significance value={event.significance} />
      </div>
      {consequence && <p className="muted">{consequence.text}</p>}
      <div className="event-badges">
        {types.map((type) => (
          <ClaimTypeBadge key={type} type={type} />
        ))}
      </div>
    </li>
  );
}
