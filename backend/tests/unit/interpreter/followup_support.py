import json
from datetime import UTC, datetime

from shared.contracts.schemas import (
    Claim,
    ClaimType,
    DepositContext,
    FollowupContext,
    HouseViewClaim,
    InsightCard,
    InterpretRequest,
    InterpretResponse,
    Role,
    SourceRef,
    Trace,
)
from tests.unit.interpreter.support import Harness

QUESTION = "А если ЦБ снизит ставку в октябре?"
NEWS_REF = SourceRef(
    kind="news",
    id="rate-news",
    title="ЦБ сохранил ключевую ставку",
    url="https://example.invalid/rate-news",
    published_at=datetime(2026, 10, 21, 12, tzinfo=UTC),
)
PROFILE_REF = SourceRef(kind="profile", id="products", title="Признак компании: products")


def rate_claim(harness: Harness, claim_id: str, **update: object) -> HouseViewClaim:
    return harness.seed.house_view[0].model_copy(
        update={
            "id": claim_id,
            "claim": "Банк ожидает снижения ключевой ставки до конца года",
            "subject": "key_rate",
            **update,
        }
    )


def deposit_trace(claim: HouseViewClaim, news_ref: SourceRef = NEWS_REF) -> Trace:
    bank_ref = SourceRef(kind="house_view", id=claim.id, title="synthetic-report, стр. 1")
    card = InsightCard(
        id="deposit-card",
        trace_id="deposit-trace",
        headline="Ставка по депозиту зависит от решения ЦБ",
        what_happened=[Claim(text="ЦБ сохранил ставку", type=ClaimType.FACT, source_ref=news_ref)],
        why_for_you=[
            Claim(text="Компания размещает депозиты", type=ClaimType.FACT, source_ref=PROFILE_REF)
        ],
        consequences=[
            Claim(
                text="Доход по депозиту зависит от ставки", type=ClaimType.AI, source_ref=NEWS_REF
            )
        ],
        actions=[Claim(text="Сравните срок размещения", type=ClaimType.AI, source_ref=PROFILE_REF)],
        bank_view=[Claim(text=claim.claim, type=ClaimType.BANK, source_ref=bank_ref)],
        basis=[news_ref, PROFILE_REF, bank_ref],
        significance=0.7,
    )
    return Trace(
        id="deposit-trace",
        request=InterpretRequest(
            user_id="private-user",
            client_id="private-client",
            role=Role.CFO,
            action_context=DepositContext(amount=5_000_000, term_days=90),
        ),
        steps=[],
        critic_verdicts=["1: ok"],
        result=InterpretResponse(silent=False, cards=[card]),
        created_at=datetime(2026, 10, 21, 12, tzinfo=UTC),
    )


def answer_draft(claim: HouseViewClaim) -> dict[str, object]:
    return {
        "headline": "Снижение ставки уменьшит доход по новым депозитам",
        "what_happened": [
            {"text": "ЦБ сохранил ставку", "type": "fact", "source": "news:rate-news"}
        ],
        "why_for_you": [
            {"text": "Компания размещает депозиты", "type": "fact", "source": "profile:products"}
        ],
        "consequences": [
            {
                "text": "При снижении ставки доход по депозиту снизится",
                "type": "ai",
                "source": f"house_view:{claim.id}",
            }
        ],
        "actions": [
            {"text": "Зафиксируйте ставку на срок", "type": "ai", "source": "profile:products"}
        ],
        "bank_view": [{"text": claim.claim, "type": "bank", "source": f"house_view:{claim.id}"}],
        "significance": 0.6,
    }


def followup_request() -> InterpretRequest:
    return InterpretRequest(
        user_id="private-user",
        client_id="private-client",
        role=Role.CFO,
        action_context=FollowupContext(card_id="deposit-card", question=QUESTION),
    )


def prompt(harness: Harness, index: int) -> dict[str, object]:
    loaded: dict[str, object] = json.loads(
        harness.llm.complete.await_args_list[index].kwargs["user"]
    )
    return loaded
