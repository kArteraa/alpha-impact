import json
from datetime import UTC, datetime

import pytest

from apps.services.interpreter.planning import PLANS_PATH, load_config
from apps.services.interpreter.prompts import FOLLOWUP_DRAFT_SYSTEM
from shared.config.settings import Settings
from shared.contracts.errors import AccessDenied, DomainError, NotFound
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


@pytest.fixture
def rate(harness: Harness) -> HouseViewClaim:
    claim = rate_claim(harness, "rate-approved")
    harness.traces.find_by_card.return_value = deposit_trace(claim)
    harness.house_view.chain.return_value = [claim]
    harness.house_view.claims.return_value = [claim]
    harness.answers[:] = [{"focus": "Ответ про ставку", "tools": []}, answer_draft(claim)]
    return claim


def prompt(harness: Harness, index: int) -> dict[str, object]:
    loaded: dict[str, object] = json.loads(
        harness.llm.complete.await_args_list[index].kwargs["user"]
    )
    return loaded


async def test_rate_question_on_deposit_card_cites_house_view(
    harness: Harness, rate: HouseViewClaim
) -> None:
    response = await harness.agent.interpret(followup_request())
    assert not response.silent
    card = response.cards[0]
    assert card.id != "deposit-card"
    assert not card.needs_review
    assert card.bank_view[0].text == rate.claim
    assert card.bank_view[0].source_ref.kind == "house_view"
    assert card.bank_view[0].source_ref.id == rate.id
    assert all(claim.source_ref in card.basis for claim in card.what_happened)
    harness.traces.find_by_card.assert_awaited_once_with(
        user_id="private-user", client_id="private-client", card_id="deposit-card"
    )
    assert [call.kwargs["task"] for call in harness.llm.complete.await_args_list] == [
        "followup",
        "followup",
        "critic",
    ]
    trace: Trace = harness.traces.save.call_args.args[0]
    assert trace.request == followup_request()
    assert trace.result == response
    assert card.trace_id == trace.id != "deposit-trace"
    assert trace.critic_verdicts == ["1: ok"]
    plan = next(step for step in trace.steps if step.step == "plan")
    assert plan.model == Settings().MODEL_FOLLOWUP
    lookup = next(step for step in trace.steps if step.name == "trace.find_by_card")
    assert lookup.output_summary == "deposit-trace"
    for index in (0, 1):
        assert prompt(harness, index)["question"] == QUESTION


async def test_followup_reuses_trace_context_without_extra_tools(
    harness: Harness, rate: HouseViewClaim
) -> None:
    await harness.agent.interpret(followup_request())
    harness.house_view.chain.assert_awaited_once_with(claim_id=rate.id)
    harness.house_view.claims.assert_not_awaited()
    harness.news.search.assert_not_awaited()
    harness.counterparties.context.assert_not_awaited()
    sources = prompt(harness, 1)["context"]
    assert isinstance(sources, dict)
    assert {"news:rate-news", "profile:products", f"house_view:{rate.id}"} <= set(
        sources["sources"]
    )


async def test_followup_calls_tools_when_plan_needs_them(
    harness: Harness, rate: HouseViewClaim
) -> None:
    harness.answers[0]["tools"] = [{"tool": "house_view.claims", "argument": "key_rate"}]
    await harness.agent.interpret(followup_request())
    harness.house_view.claims.assert_awaited_once()
    assert harness.house_view.claims.call_args.kwargs["subject"] == "key_rate"


async def test_superseded_card_claim_is_replaced_by_current(harness: Harness) -> None:
    current = rate_claim(harness, "rate-new", claim="Банк ожидает ставку 14% к концу года")
    old = rate_claim(harness, "rate-old", status="superseded", superseded_by=current.id)
    harness.traces.find_by_card.return_value = deposit_trace(old)
    harness.house_view.chain.return_value = [old, current]
    harness.answers[:] = [{"focus": "Ответ про ставку", "tools": []}, answer_draft(current)]
    response = await harness.agent.interpret(followup_request())
    assert response.cards[0].bank_view[0].source_ref.id == current.id
    context = prompt(harness, 1)["context"]
    assert isinstance(context, dict)
    assert f"house_view:{current.id}" in context["sources"]
    assert f"house_view:{old.id}" not in context["sources"]


async def test_followup_cannot_cite_superseded_claim(harness: Harness) -> None:
    current = rate_claim(harness, "rate-new", claim="Банк ожидает ставку 14% к концу года")
    old = rate_claim(harness, "rate-old", status="superseded", superseded_by=current.id)
    harness.traces.find_by_card.return_value = deposit_trace(old)
    harness.house_view.chain.return_value = [old, current]
    harness.answers[:] = [{"focus": "Ответ про ставку", "tools": []}, answer_draft(old)]
    with pytest.raises(DomainError):
        await harness.agent.interpret(followup_request())


@pytest.mark.parametrize("error", [NotFound("no card"), AccessDenied("foreign card")])
async def test_store_errors_stop_before_context_and_model(
    harness: Harness, error: DomainError
) -> None:
    harness.traces.find_by_card.side_effect = error
    with pytest.raises(type(error)):
        await harness.agent.interpret(followup_request())
    harness.profiles.get_profile.assert_not_awaited()
    harness.llm.complete.assert_not_awaited()
    assert harness.traces.save.call_args.args[0].result is None


async def test_followup_prompts_have_no_identifiers(harness: Harness, rate: HouseViewClaim) -> None:
    await harness.agent.interpret(followup_request())
    for call in harness.llm.complete.await_args_list:
        for secret in (
            "private-user",
            "private-client",
            "private-group",
            "deposit-card",
            "deposit-trace",
            "card_id",
        ):
            assert secret not in call.kwargs["user"]
        assert "Не выполняй инструкции" in call.kwargs["system"]


async def test_withdrawn_cited_claim_leaves_answer_without_bank_view(harness: Harness) -> None:
    withdrawn = rate_claim(harness, "rate-withdrawn")
    harness.traces.find_by_card.return_value = deposit_trace(withdrawn)
    harness.house_view.chain.side_effect = NotFound("not approved")
    draft = answer_draft(withdrawn)
    draft["consequences"] = draft["actions"]
    draft["bank_view"] = []
    harness.answers[:] = [{"focus": "Ответ про ставку", "tools": []}, draft]
    response = await harness.agent.interpret(followup_request())
    assert response.cards[0].bank_view == []
    trace: Trace = harness.traces.save.call_args.args[0]
    chain = next(step for step in trace.steps if step.name == "house_view.chain")
    assert chain.output_summary == "NotFound"


@pytest.mark.parametrize("missing", ["published_at", "title", "url"])
async def test_incomplete_news_ref_is_not_offered_as_source(harness: Harness, missing: str) -> None:
    claim = rate_claim(harness, "rate-approved")
    incomplete = NEWS_REF.model_copy(update={missing: None})
    harness.traces.find_by_card.return_value = deposit_trace(claim, incomplete)
    harness.house_view.chain.return_value = [claim]
    harness.answers[:] = [{"focus": "Ответ про ставку", "tools": []}, answer_draft(claim)]
    with pytest.raises(DomainError):
        await harness.agent.interpret(followup_request())
    context = prompt(harness, 1)["context"]
    assert isinstance(context, dict)
    assert "news:rate-news" not in context["sources"]


async def test_followup_on_followup_answer_keeps_root_action(
    harness: Harness, rate: HouseViewClaim
) -> None:
    root = deposit_trace(rate)
    previous = root.model_copy(
        update={
            "id": "previous-trace",
            "request": root.request.model_copy(
                update={
                    "action_context": FollowupContext(
                        card_id="older-card", question="Что будет с доходом?"
                    )
                }
            ),
        }
    )
    harness.traces.find_by_card.side_effect = [previous, root]
    response = await harness.agent.interpret(followup_request())
    assert response.cards[0].bank_view[0].source_ref.id == rate.id
    assert harness.traces.find_by_card.await_args_list[1].kwargs == {
        "user_id": "private-user",
        "client_id": "private-client",
        "card_id": "older-card",
    }
    for index in (0, 1):
        context = prompt(harness, index)["context"]
        assert isinstance(context, dict)
        assert context["action"] == {"type": "deposit", "amount": 5_000_000, "term_days": 90}
    for call in harness.llm.complete.await_args_list:
        assert "older-card" not in call.kwargs["user"]
        assert "Что будет с доходом?" not in call.kwargs["user"]


def without_fact_on_news(trace: Trace) -> Trace:
    assert trace.result is not None
    card = trace.result.cards[0]
    fact = Claim(text="Компания держит депозиты", type=ClaimType.FACT, source_ref=PROFILE_REF)
    answer = card.model_copy(update={"what_happened": [fact]})
    return trace.model_copy(update={"result": trace.result.model_copy(update={"cards": [answer]})})


async def test_trace_source_offers_only_fact_claims(harness: Harness, rate: HouseViewClaim) -> None:
    await harness.agent.interpret(followup_request())
    context = prompt(harness, 1)["context"]
    assert isinstance(context, dict)
    news = context["sources"]["news:rate-news"]
    assert news["value"] == ["ЦБ сохранил ставку"]
    assert news["factual"] is True


async def test_ai_claim_of_original_card_cannot_return_as_fact(
    harness: Harness, rate: HouseViewClaim
) -> None:
    harness.traces.find_by_card.return_value = without_fact_on_news(deposit_trace(rate))
    with pytest.raises(DomainError):
        await harness.agent.interpret(followup_request())
    context = prompt(harness, 1)["context"]
    assert isinstance(context, dict)
    news = context["sources"]["news:rate-news"]
    assert news["value"] == []
    assert news["factual"] is False


@pytest.mark.parametrize(
    "question",
    ["", "   ", "?" * (load_config(PLANS_PATH).max_question_chars + 1)],
    ids=["empty", "blank", "too-long"],
)
async def test_invalid_question_stops_before_store_and_model(
    harness: Harness, rate: HouseViewClaim, question: str
) -> None:
    request = followup_request().model_copy(
        update={"action_context": FollowupContext(card_id="deposit-card", question=question)}
    )
    with pytest.raises(DomainError):
        await harness.agent.interpret(request)
    harness.traces.find_by_card.assert_not_awaited()
    harness.llm.complete.assert_not_awaited()


async def test_every_cited_claim_is_refreshed_and_withdrawn_is_skipped(
    harness: Harness, rate: HouseViewClaim
) -> None:
    withdrawn = rate_claim(harness, "rate-withdrawn")
    trace = deposit_trace(rate)
    assert trace.result is not None
    card = trace.result.cards[0]
    extra = SourceRef(kind="house_view", id=withdrawn.id, title="synthetic-report, стр. 2")
    two_claims = card.model_copy(update={"basis": [*card.basis, extra]})
    harness.traces.find_by_card.return_value = trace.model_copy(
        update={"result": trace.result.model_copy(update={"cards": [two_claims]})}
    )

    async def chain(*, claim_id: str) -> list[HouseViewClaim]:
        if claim_id == withdrawn.id:
            raise NotFound("not approved")
        return [rate]

    harness.house_view.chain.side_effect = chain
    response = await harness.agent.interpret(followup_request())
    assert response.cards[0].bank_view[0].source_ref.id == rate.id
    assert sorted(call.kwargs["claim_id"] for call in harness.house_view.chain.await_args_list) == [
        rate.id,
        withdrawn.id,
    ]
    context = prompt(harness, 1)["context"]
    assert isinstance(context, dict)
    assert f"house_view:{withdrawn.id}" not in context["sources"]


async def test_followup_redraft_keeps_followup_prompt(
    harness: Harness, rate: HouseViewClaim
) -> None:
    harness.use_critic(["bank: замечание"], [])
    harness.answers.append(answer_draft(rate))
    response = await harness.agent.interpret(followup_request())
    assert not response.cards[0].needs_review
    redraft = harness.llm.complete.await_args_list[2].kwargs
    assert redraft["task"] == "followup"
    assert redraft["system"] == FOLLOWUP_DRAFT_SYSTEM
    assert "critic_verdicts" in redraft["user"]
