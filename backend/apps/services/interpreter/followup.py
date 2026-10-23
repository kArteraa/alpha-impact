from dataclasses import replace

from apps.services.interpreter.calculation import calculation_evidence
from apps.services.interpreter.context import Evidence, prompt_context, source_key, sources
from apps.services.interpreter.drafting import CLAIM_BLOCKS, card_claims
from shared.contracts.errors import DomainError, NotFound
from shared.contracts.schemas import (
    ClaimType,
    ClientProfile,
    CounterpartyContext,
    FollowupContext,
    HouseViewClaim,
    InsightCard,
    InterpretRequest,
    NewsItem,
    SourceRef,
    Trace,
)

TRACE_NEWS_SOURCE = "trace"
NEWS_REF_FIELDS = {"id", "title", "url", "published_at"}


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


def traceable_news(ref: SourceRef) -> bool:
    return (
        ref.kind == "news"
        and ref.title is not None
        and ref.url is not None
        and ref.published_at is not None
    )


def trace_news(card: InsightCard) -> list[NewsItem]:
    facts = [claim for claim in card_claims(card) if claim.type == ClaimType.FACT]
    return [
        NewsItem.model_validate(
            {
                **ref.model_dump(include=NEWS_REF_FIELDS),
                "text": "\n".join(claim.text for claim in facts if claim.source_ref == ref),
                "source": TRACE_NEWS_SOURCE,
                "entities": [],
                "factors": [],
            }
        )
        for ref in card.basis
        if traceable_news(ref)
    ]


def cited_house_view(card: InsightCard) -> list[str]:
    return sorted({ref.id for ref in card.basis if ref.kind == "house_view"})


def checked_followup(action: FollowupContext, limit: int) -> FollowupContext:
    question = action.question.strip()
    if not question or len(question) > limit:
        raise DomainError(f"Followup question is empty or longer than {limit} characters")
    return action.model_copy(update={"question": question})


def followup_evidence(
    card: InsightCard,
    profile: ClientProfile,
    counterparty: CounterpartyContext | None,
    house_view: list[HouseViewClaim],
) -> dict[str, Evidence]:
    news = trace_news(card)
    evidence = {
        **sources(profile, counterparty, news, house_view),
        **calculation_evidence(card.calculation),
    }
    unfactual = {item.id for item in news if not item.text}
    return {
        key: replace(item, factual=False)
        if item.ref.kind == "news" and item.ref.id in unfactual
        else item
        for key, item in evidence.items()
    }


def followup_payload(
    question: str,
    request: InterpretRequest,
    card: InsightCard,
    profile: ClientProfile,
    counterparty: CounterpartyContext | None,
    evidence: dict[str, Evidence],
) -> dict[str, object]:
    return {
        "question": question,
        "card": card_view(card),
        "context": prompt_context(request, profile, counterparty, evidence),
    }
