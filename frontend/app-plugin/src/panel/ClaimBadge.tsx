import type { Claim } from "../types";
import { CLAIM_BADGES, sourceTitle } from "./labels";

export function ClaimBadge({ claim }: { claim: Claim }) {
  const badge = CLAIM_BADGES[claim.type];
  const title = sourceTitle(claim.source_ref);
  const label = `${badge.label} — источник: ${title}`;
  const content = (
    <>
      <span className="claim-badge-icon" aria-hidden="true">
        {badge.icon}
      </span>
      {badge.label}
    </>
  );
  if (claim.source_ref.url) {
    return (
      <a
        className="claim-badge"
        data-claim-type={claim.type}
        href={claim.source_ref.url}
        target="_blank"
        rel="noreferrer"
        title={title}
        aria-label={label}
      >
        {content}
      </a>
    );
  }
  return (
    <span className="claim-badge" data-claim-type={claim.type} title={title} aria-label={label}>
      {content}
    </span>
  );
}
