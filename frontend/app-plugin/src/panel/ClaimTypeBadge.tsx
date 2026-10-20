import type { ClaimType } from "../types";
import { CLAIM_BADGES } from "./labels";

export function BadgeContent({ type }: { type: ClaimType }) {
  const badge = CLAIM_BADGES[type];
  return (
    <>
      <span className="claim-badge-icon" aria-hidden="true">
        {badge.icon}
      </span>
      {badge.label}
    </>
  );
}

export function ClaimTypeBadge({ type }: { type: ClaimType }) {
  return (
    <span className="claim-badge" data-claim-type={type} aria-label={CLAIM_BADGES[type].label}>
      <BadgeContent type={type} />
    </span>
  );
}
