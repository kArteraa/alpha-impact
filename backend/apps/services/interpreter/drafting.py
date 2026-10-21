from pydantic import BaseModel, ConfigDict, Field

from apps.services.interpreter.context import Evidence
from shared.contracts.errors import DomainError
from shared.contracts.schemas import Claim, ClaimType, InsightCard, SourceRef


class DraftClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str = Field(min_length=1)
    type: ClaimType
    source: str = Field(min_length=1)


class Draft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    headline: str = Field(min_length=1)
    what_happened: list[DraftClaim] = Field(min_length=1)
    why_for_you: list[DraftClaim] = Field(min_length=1)
    consequences: list[DraftClaim] = Field(min_length=1)
    actions: list[DraftClaim] = Field(min_length=1)
    bank_view: list[DraftClaim]
    significance: float = Field(ge=0, le=1)


def build_card(
    draft: Draft, evidence: dict[str, Evidence], card_id: str, trace_id: str
) -> InsightCard:
    basis: dict[str, SourceRef] = {}

    def resolve(claims: list[DraftClaim], bank_only: bool) -> list[Claim]:
        result = []
        for claim in claims:
            item = evidence.get(claim.source)
            if item is None:
                raise DomainError("Draft cites a source outside the collected context")
            if bank_only and claim.type != ClaimType.BANK:
                raise DomainError("Bank view must contain bank claims")
            if claim.type == ClaimType.BANK and (
                item.bank_text is None or claim.text != item.bank_text
            ):
                raise DomainError("Bank claim must quote an approved house view claim")
            if claim.type == ClaimType.FACT and not item.factual:
                raise DomainError("An inferred feature or forecast cannot be cited as a fact")
            basis[claim.source] = item.ref
            result.append(Claim(text=claim.text, type=claim.type, source_ref=item.ref))
        return result

    blocks = {
        name: resolve(getattr(draft, name), name == "bank_view")
        for name in ("what_happened", "why_for_you", "consequences", "actions", "bank_view")
    }
    return InsightCard(
        id=card_id,
        trace_id=trace_id,
        headline=draft.headline,
        what_happened=blocks["what_happened"],
        why_for_you=blocks["why_for_you"],
        consequences=blocks["consequences"],
        actions=blocks["actions"],
        bank_view=blocks["bank_view"],
        basis=list(basis.values()),
        significance=draft.significance,
    )
