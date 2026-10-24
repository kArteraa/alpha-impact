import type { Claim } from "../types";
import { ClaimBadge } from "./ClaimBadge";
import { SOURCE_KINDS, sourceTitle } from "./labels";

export function ClaimList({ claims, withTraits = false }: { claims: Claim[]; withTraits?: boolean }) {
  return (
    <ul className="insight-claims">
      {claims.map((claim, index) => (
        <li key={index}>
          <ClaimBadge claim={claim} />
          <span className="claim-text">
            {claim.text}
            {withTraits && SOURCE_KINDS[claim.source_ref.kind].trait && claim.source_ref.title && (
              <span className="insight-chip">{sourceTitle(claim.source_ref)}</span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
