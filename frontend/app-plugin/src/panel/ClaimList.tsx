import type { Claim } from "../types";
import { ClaimBadge } from "./ClaimBadge";
import { TRAIT_SOURCES } from "./labels";

export function ClaimList({ claims, withTraits = false }: { claims: Claim[]; withTraits?: boolean }) {
  return (
    <ul className="claims">
      {claims.map((claim, index) => (
        <li key={index}>
          <ClaimBadge claim={claim} />
          <span className="claim-text">
            {claim.text}
            {withTraits && TRAIT_SOURCES.has(claim.source_ref.kind) && claim.source_ref.title && (
              <span className="chip">{claim.source_ref.title}</span>
            )}
          </span>
        </li>
      ))}
    </ul>
  );
}
