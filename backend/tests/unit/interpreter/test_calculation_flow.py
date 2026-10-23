import json
from datetime import UTC, date, datetime, timedelta

import pytest

from apps.services.interpreter.calculation import KEY_RATE
from shared.contracts.schemas import (
    ActionContext,
    DepositContext,
    Factor,
    HouseViewClaim,
    InterpretRequest,
    LoanContext,
    NewsItem,
    Trace,
)
from tests.unit.interpreter.followup_support import followup_request
from tests.unit.interpreter.support import Harness

TODAY = datetime.now(UTC).date()


def key_rate_claim(
    claim_id: str, kind: str, value: str, day: date, valid_until: date | None
) -> HouseViewClaim:
    return HouseViewClaim(
        id=claim_id,
        claim=f"Банк: ключевая ставка {value}",
        type=kind,
        subject=KEY_RATE,
        value=value,
        date=day,
        valid_until=valid_until,
        source_doc="macro.pdf",
        page=2,
        superseded_by=None,
        status="approved",
    )


RATES = [
    key_rate_claim("rate-fact", "fact", "14,0%", TODAY - timedelta(days=40), None),
    key_rate_claim(
        "rate-year", "forecast", "14,0%", TODAY - timedelta(days=40), TODAY + timedelta(days=70)
    ),
    key_rate_claim(
        "rate-next", "forecast", "12,0%", TODAY - timedelta(days=40), TODAY + timedelta(days=435)
    ),
]
FORECAST = RATES[2]
RATE_NEWS = NewsItem(
    id="rate-news",
    title="ЦБ сохранил ключевую ставку",
    text="Синтетическая новость о ключевой ставке",
    url="https://example.invalid/rate-news",
    published_at=datetime.now(UTC),
    source="synthetic",
    entities=[],
    factors=[Factor(name=KEY_RATE, direction="down", strength=1.0, horizon="quarter")],
)


def rate_draft(calc: str | None) -> dict[str, object]:
    consequence = calc or "house_view:rate-next"
    return {
        "headline": "Ставка банка влияет на решение",
        "what_happened": [
            {"text": "ЦБ сохранил ставку", "type": "fact", "source": "news:rate-news"}
        ],
        "why_for_you": [
            {"text": "Компания пользуется расчётами", "type": "fact", "source": "profile:products"}
        ],
        "consequences": [{"text": "Итог расчёта", "type": "ai", "source": consequence}],
        "actions": [{"text": "Сравните сроки", "type": "ai", "source": "profile:products"}],
        "bank_view": [{"text": FORECAST.claim, "type": "bank", "source": "house_view:rate-next"}],
        "significance": 0.6,
    }


def moment(harness: Harness, action: ActionContext, calc: str | None) -> InterpretRequest:
    profile = harness.profiles.get_profile.return_value
    harness.profiles.get_profile.return_value = profile.model_copy(
        update={"exposures": {**profile.exposures, KEY_RATE: 1.0}}
    )
    harness.news.search.return_value = [RATE_NEWS]
    harness.house_view.claims.side_effect = lambda subject, as_of: [
        claim for claim in RATES if claim.subject == subject
    ]
    harness.answers[:] = [{"focus": "Ставка", "tools": []}, rate_draft(calc)]
    return harness.request().model_copy(update={"action_context": action})


def saved(harness: Harness) -> Trace:
    trace: Trace = harness.traces.save.call_args.args[0]
    return trace


def tool_names(harness: Harness) -> list[str]:
    return [step.name for step in saved(harness).steps if step.step == "tool"]


def draft_sources(harness: Harness) -> dict[str, object]:
    payload = json.loads(harness.llm.complete.await_args_list[1].kwargs["user"])
    sources: dict[str, object] = payload["context"]["sources"]
    return sources


async def test_deposit_card_carries_calculation_on_bank_rate_path(harness: Harness) -> None:
    action = DepositContext(amount=10_000_000, term_days=90)
    response = await harness.agent.interpret(moment(harness, action, "calc:deposit_terms"))
    card = response.cards[0]
    assert card.calculation is not None
    assert card.calculation.kind == "deposit_terms"
    assert card.calculation.formula.startswith("фиксация: 10 000 000 ₽ × 14% × 90/365")
    assert (
        "ставка депозита следует ключевой ставке по позиции банка" in card.calculation.assumptions
    )
    assert card.consequences[0].source_ref.kind == "calc"
    assert card.consequences[0].source_ref in card.basis
    assert card.bank_view[0].source_ref.id == FORECAST.id
    assert not card.needs_review
    assert "calc:deposit_terms" in draft_sources(harness)
    assert {"house_view.claims", "whatif.deposit_terms"} <= set(tool_names(harness))
    harness.house_view.claims.assert_any_await(subject=KEY_RATE, as_of=TODAY)


async def test_floating_loan_card_carries_rate_burden(harness: Harness) -> None:
    action = LoanContext(product="loan", amount=50_000_000, rate_type="floating")
    response = await harness.agent.interpret(moment(harness, action, "calc:rate_burden"))
    calculation = response.cards[0].calculation
    assert calculation is not None
    assert calculation.kind == "rate_burden"
    assert calculation.value < 0
    assert "whatif.rate_burden" in tool_names(harness)


@pytest.mark.parametrize("rate_type", ["fixed", None])
async def test_loan_without_floating_rate_cites_bank_rate_without_calculation(
    harness: Harness, rate_type: str | None
) -> None:
    action = LoanContext.model_validate({"product": "loan", "amount": 1e7, "rate_type": rate_type})
    response = await harness.agent.interpret(moment(harness, action, None))
    card = response.cards[0]
    assert card.calculation is None
    assert card.bank_view[0].source_ref.id == FORECAST.id
    assert not any(name.startswith("whatif.") for name in tool_names(harness))
    assert not any(key.startswith("calc:") for key in draft_sources(harness))


async def test_rate_claims_reach_draft_even_without_rate_news(harness: Harness) -> None:
    action = DepositContext(amount=1_000_000, term_days=30)
    request = moment(harness, action, "calc:deposit_terms")
    harness.news.search.return_value = [
        RATE_NEWS.model_copy(
            update={
                "factors": [
                    Factor(name="labor_market", direction="up", strength=1.0, horizon="month")
                ]
            }
        )
    ]
    profile = harness.profiles.get_profile.return_value
    harness.profiles.get_profile.return_value = profile.model_copy(
        update={"exposures": {**profile.exposures, "labor_market": 1.0}}
    )
    response = await harness.agent.interpret(request)
    assert response.cards[0].calculation is not None
    assert f"house_view:{FORECAST.id}" in draft_sources(harness)


async def test_payment_gets_no_rate_step_or_calculation(harness: Harness) -> None:
    response = await harness.agent.interpret(harness.request())
    assert response.cards[0].calculation is None
    assert not any(name.startswith("whatif.") for name in tool_names(harness))
    assert all(
        call.kwargs["subject"] != KEY_RATE for call in harness.house_view.claims.await_args_list
    )


async def test_followup_answer_has_no_calculation(harness: Harness, rate: HouseViewClaim) -> None:
    response = await harness.agent.interpret(followup_request())
    assert response.cards[0].calculation is None
    assert not any(name.startswith("whatif.") for name in tool_names(harness))
