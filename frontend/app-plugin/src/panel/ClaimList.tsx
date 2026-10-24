import type { Claim } from "../types";
import { ClaimBadge } from "./ClaimBadge";
import { knownTitle, SOURCE_KINDS } from "./labels";

export function ClaimList({ claims, withTraits = false }: { claims: Claim[]; withTraits?: boolean }) {
  return (
    <ul className="insight-claims">
      {claims.map((claim, index) => {
        const trait = withTraits && SOURCE_KINDS[claim.source_ref.kind].trait ? knownTitle(claim.source_ref) : null;
        return (
          <li key={index}>
            <ClaimBadge claim={claim} />
            <span className="claim-text">
              {claim.text}
              {trait && <span className="insight-chip">{trait}</span>}
            </span>
          </li>
        );
      })}
    </ul>
  );
}
