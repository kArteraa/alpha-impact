import re
from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field

from apps.services.interpreter.context import Evidence
from shared.contracts.errors import DomainError
from shared.contracts.schemas import Claim, ClaimType, InsightCard, SourceRef

CLAIM_BLOCKS = ("what_happened", "why_for_you", "consequences", "actions", "bank_view")
REQUIRED_BLOCKS = CLAIM_BLOCKS[:-1]
SOURCE_KEY_CHARS = 64


def card_claims(card: InsightCard) -> list[Claim]:
    return [claim for name in CLAIM_BLOCKS for claim in getattr(card, name)]


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


def words(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold())


def starts_like(text: str, quote: str) -> bool:
    said = words(text)
    return bool(said) and said == words(quote)[: len(said)]


@dataclass
class BuildNotes:
    rewrite: list[str] = field(default_factory=list)
    remarks: list[str] = field(default_factory=list)


def check_quote(claim: DraftClaim, quotes: dict[str, str], notes: BuildNotes) -> None:
    if starts_like(claim.text, quotes[claim.source]):
        return
    other = next(
        (
            key
            for key, quote in quotes.items()
            if key != claim.source and starts_like(claim.text, quote)
        ),
        None,
    )
    if other is None:
        notes.remarks.append(
            f"bank: тезис со ссылкой на {claim.source} — трактовка модели «{claim.text}», "
            "в карточке цитата утверждения по ссылке"
        )
        return
    notes.rewrite.append(
        f"bank: тезис со ссылкой на {claim.source} начинается как утверждение {other}: "
        f"«{claim.text}»"
    )


def without_quoted(
    name: str, block: list[Claim], quoted: list[Claim], notes: BuildNotes
) -> list[Claim]:
    rest = [claim for claim in block if claim not in quoted]
    if rest:
        return rest
    notes.rewrite.append(f"{name}: состоит только из цитаты позиции банка")
    return block


def with_quotes(draft: Draft, evidence: dict[str, Evidence]) -> Draft:
    def quoted(claim: DraftClaim) -> DraftClaim:
        quote = evidence[claim.source].bank_text
        if claim.type != ClaimType.BANK or quote is None:
            return claim
        return claim.model_copy(update={"text": quote})

    return draft.model_copy(
        update={name: [quoted(claim) for claim in getattr(draft, name)] for name in CLAIM_BLOCKS}
    )


def build_card(
    draft: Draft, evidence: dict[str, Evidence], card_id: str, trace_id: str
) -> tuple[InsightCard, BuildNotes]:
    basis: dict[str, SourceRef] = {}
    notes = BuildNotes()
    quotes = {key: item.bank_text for key, item in evidence.items() if item.bank_text is not None}

    def resolve(claims: list[DraftClaim], bank_only: bool) -> list[Claim]:
        result = []
        for claim in claims:
            item = evidence.get(claim.source)
            if item is None:
                raise DomainError(
                    "Draft cites a source outside the collected context: "
                    f"{claim.source[:SOURCE_KEY_CHARS]}"
                )
            if bank_only and claim.type != ClaimType.BANK:
                raise DomainError("Bank view must contain bank claims")
            text = claim.text
            if claim.type == ClaimType.BANK:
                if item.bank_text is None:
                    raise DomainError("Bank claim must quote an approved house view claim")
                text = item.bank_text
                check_quote(claim, quotes, notes)
            if claim.type == ClaimType.FACT and not item.factual:
                raise DomainError("An inferred feature or forecast cannot be cited as a fact")
            basis[claim.source] = item.ref
            resolved = Claim(text=text, type=claim.type, source_ref=item.ref)
            if resolved not in result:
                result.append(resolved)
        return result

    blocks = {name: resolve(getattr(draft, name), name == "bank_view") for name in CLAIM_BLOCKS}
    bank_view = blocks["bank_view"]
    required = {
        name: without_quoted(name, blocks[name], bank_view, notes) for name in REQUIRED_BLOCKS
    }
    card = InsightCard(
        id=card_id,
        trace_id=trace_id,
        headline=draft.headline,
        **required,
        bank_view=bank_view,
        basis=list(basis.values()),
        significance=draft.significance,
    )
    return card, notes
