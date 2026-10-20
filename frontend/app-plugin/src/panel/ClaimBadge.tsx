import type { Claim } from "../types";
import { BadgeContent } from "./ClaimTypeBadge";
import { CLAIM_BADGES, sourceTitle } from "./labels";
import { SourceLink } from "./SourceLink";

export function ClaimBadge({ claim }: { claim: Claim }) {
  const title = sourceTitle(claim.source_ref);
  return (
    <SourceLink
      source={claim.source_ref}
      className="claim-badge"
      data-claim-type={claim.type}
      title={title}
      aria-label={`${CLAIM_BADGES[claim.type].label} — источник: ${title}`}
    >
      <BadgeContent type={claim.type} />
    </SourceLink>
  );
}
