import json

from pydantic import BaseModel, ConfigDict

from apps.services.interpreter.prompts import CRITIC_SYSTEM
from shared.contracts.ports import LLMGateway
from shared.contracts.schemas import Claim, ClaimType, HouseViewClaim, InsightCard, NewsItem

DIVERGENCE_MARK = "расхождение"
CLIENT_SOURCES = {"profile", "graph"}


class Contradiction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    claim: str
    house_view_id: str
    reason: str


class Contradictions(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[Contradiction]


def claims(card: InsightCard) -> list[Claim]:
    return [
        *card.what_happened,
        *card.why_for_you,
        *card.consequences,
        *card.actions,
        *card.bank_view,
    ]


def source_verdicts(
    card: InsightCard, house_view: list[HouseViewClaim], news: list[NewsItem]
) -> list[str]:
    known = {"news": {item.id for item in news}, "house_view": {claim.id for claim in house_view}}
    result = []
    for claim in claims(card):
        ref = claim.source_ref
        if not ref.id or ref.id not in known.get(ref.kind, {ref.id}):
            result.append(f"source: «{claim.text}» ссылается на неизвестный источник {ref.kind}")
        elif ref not in card.basis:
            result.append(f"source: источник «{claim.text}» не указан в basis")
    return result


def bank_verdicts(card: InsightCard, house_view: list[HouseViewClaim]) -> list[str]:
    current = {
        claim.id: claim
        for claim in house_view
        if claim.status == "approved" and claim.superseded_by is None
    }
    result = [
        f"bank: в позиции банка тезис типа {claim.type.value}: «{claim.text}»"
        for claim in card.bank_view
        if claim.type != ClaimType.BANK
    ]
    for claim in claims(card):
        if claim.type != ClaimType.BANK:
            continue
        quoted = current.get(claim.source_ref.id) if claim.source_ref.kind == "house_view" else None
        if quoted is None:
            result.append(f"bank: «{claim.text}» не ссылается на актуальное утверждение банка")
        elif claim.text != quoted.claim:
            result.append(f"bank: «{claim.text}» не цитирует утверждение {quoted.id} дословно")
    return result


def retelling_verdicts(card: InsightCard) -> list[str]:
    refs = {(claim.source_ref.kind, claim.source_ref.id) for claim in claims(card)}
    result = []
    if len(refs) < 2:
        result.append("retelling: карточка опирается меньше чем на два источника")
    if not any(kind in CLIENT_SOURCES for kind, _ in refs):
        result.append("retelling: нет ни одного признака компании или агрегата получателя")
    return result


class CriticAgent:
    def __init__(self, llm: LLMGateway) -> None:
        self._llm = llm

    async def review(
        self, card: InsightCard, house_view: list[HouseViewClaim], news: list[NewsItem]
    ) -> list[str]:
        return [
            *source_verdicts(card, house_view, news),
            *bank_verdicts(card, house_view),
            *await self._contradictions(card, house_view),
            *retelling_verdicts(card),
        ]

    async def _contradictions(
        self, card: InsightCard, house_view: list[HouseViewClaim]
    ) -> list[str]:
        if not house_view:
            return []
        checked = {claim.text for claim in claims(card) if claim.type != ClaimType.BANK}
        user = json.dumps(
            {
                "claims": sorted(checked),
                "house_view": [
                    {
                        "id": claim.id,
                        "claim": claim.claim,
                        "subject": claim.subject,
                        "value": claim.value,
                    }
                    for claim in house_view
                ],
            },
            ensure_ascii=False,
        )
        raw, _, _ = await self._llm.complete(
            task="critic", system=CRITIC_SYSTEM, user=user, schema=Contradictions
        )
        known = {claim.id for claim in house_view}
        return [
            f"contradiction: «{item.claim}» противоречит {item.house_view_id}: {item.reason}"
            for item in Contradictions.model_validate(raw).items
            if item.claim in checked
            and item.house_view_id in known
            and DIVERGENCE_MARK not in item.claim.lower()
        ]
