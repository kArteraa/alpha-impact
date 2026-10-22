from apps.services.interpreter.context import Evidence, prompt_context, source_key, sources
from apps.services.interpreter.drafting import CLAIM_BLOCKS, card_claims
from shared.contracts.errors import NotFound
from shared.contracts.schemas import (
    ClientProfile,
    HouseViewClaim,
    InsightCard,
    InterpretRequest,
    NewsItem,
    Trace,
)

TRACE_SOURCES = {"news", "graph"}
TRACE_NEWS_SOURCE = "trace"


def original_card(trace: Trace, card_id: str) -> InsightCard:
    cards = [] if trace.result is None else trace.result.cards
    card = next((card for card in cards if card.id == card_id), None)
    if card is None:
        raise NotFound(f"Unknown card {card_id}")
    return card


def card_view(card: InsightCard) -> dict[str, object]:
    return {
        "headline": card.headline,
        **{
            name: [
                {
                    "text": claim.text,
                    "type": claim.type.value,
                    "source": source_key(claim.source_ref),
                }
                for claim in getattr(card, name)
            ]
            for name in CLAIM_BLOCKS
        },
    }


def trace_evidence(card: InsightCard) -> dict[str, Evidence]:
    claims = card_claims(card)
    return {
        source_key(ref): Evidence(
            ref,
            [claim.text for claim in claims if claim.source_ref == ref],
            None,
            True,
        )
        for ref in card.basis
        if ref.kind in TRACE_SOURCES
    }


def trace_news(card: InsightCard) -> list[NewsItem]:
    return [
        NewsItem(
            id=ref.id,
            title=ref.title or ref.id,
            text="",
            url=ref.url or "",
            published_at=ref.published_at,
            source=TRACE_NEWS_SOURCE,
            entities=[],
            factors=[],
        )
        for ref in card.basis
        if ref.kind == "news" and ref.published_at is not None
    ]


def cited_house_view(card: InsightCard) -> list[str]:
    return sorted({ref.id for ref in card.basis if ref.kind == "house_view"})


def followup_evidence(
    card: InsightCard, profile: ClientProfile, house_view: list[HouseViewClaim]
) -> dict[str, Evidence]:
    return {**sources(profile, None, [], house_view), **trace_evidence(card)}


def followup_payload(
    question: str,
    request: InterpretRequest,
    card: InsightCard,
    profile: ClientProfile,
    evidence: dict[str, Evidence],
) -> dict[str, object]:
    return {
        "question": question,
        "card": card_view(card),
        "context": prompt_context(request, profile, None, evidence),
    }
