import pytest
from pydantic import ConfigDict

from apps.services.interpreter import followup
from apps.services.interpreter.planning import PLANS_PATH, load_config
from shared.contracts.errors import DomainError
from shared.contracts.schemas import (
    Claim,
    ClaimType,
    FollowupContext,
    HouseViewClaim,
    NewsItem,
    SourceRef,
    Trace,
)
from tests.unit.interpreter.followup_support import (
    answer_draft,
    deposit_trace,
    followup_request,
    prompt,
    rate_claim,
)
from tests.unit.interpreter.support import Harness


def payment_trace(harness: Harness, claim: HouseViewClaim, field: str) -> Trace:
    trace = deposit_trace(claim)
    assert trace.result is not None
    graph_ref = SourceRef(kind="graph", id=field, title=f"Контекст контрагента: {field}")
    card = trace.result.cards[0]
    guess = Claim(text="Поставщик зависит от ставки", type=ClaimType.AI, source_ref=graph_ref)
    answered = card.model_copy(update={"consequences": [guess], "basis": [*card.basis, graph_ref]})
    return trace.model_copy(
        update={
            "request": harness.request(),
            "result": trace.result.model_copy(update={"cards": [answered]}),
        }
    )


def aggregate_field(harness: Harness) -> str:
    aggregates = harness.seed.counterparties["logistics"].model_dump()
    return next(name for name, value in aggregates.items() if value is not None)


async def test_payment_followup_reads_recipient_aggregates_as_facts(harness: Harness) -> None:
    claim = rate_claim(harness, "rate-approved")
    field = aggregate_field(harness)
    harness.traces.find_by_card.return_value = payment_trace(harness, claim, field)
    harness.house_view.chain.return_value = [claim]
    draft = answer_draft(claim)
    draft["why_for_you"] = [
        {"text": "Получатель из отрасли поставок", "type": "fact", "source": f"graph:{field}"}
    ]
    harness.answers[:] = [{"focus": "Ответ про ставку", "tools": []}, draft]
    response = await harness.agent.interpret(followup_request())
    assert not response.cards[0].needs_review
    payment = harness.seed.payment
    harness.counterparties.context.assert_awaited_once_with(
        "private-client", "logistics", payment.inn
    )
    context = prompt(harness, 1)["context"]
    assert isinstance(context, dict)
    graph = context["sources"][f"graph:{field}"]
    assert graph["value"] == harness.seed.counterparties["logistics"].model_dump()[field]
    assert graph["factual"] is True


async def test_failed_chain_stops_refreshing_other_claims(
    harness: Harness, rate: HouseViewClaim
) -> None:
    withdrawn = rate_claim(harness, "rate-withdrawn")
    trace = deposit_trace(rate)
    assert trace.result is not None
    card = trace.result.cards[0]
    extra = SourceRef(kind="house_view", id=withdrawn.id, title="synthetic-report, стр. 2")
    harness.traces.find_by_card.return_value = trace.model_copy(
        update={
            "result": trace.result.model_copy(
                update={"cards": [card.model_copy(update={"basis": [*card.basis, extra]})]}
            )
        }
    )
    harness.house_view.chain.side_effect = RuntimeError("store is down")
    with pytest.raises(RuntimeError):
        await harness.agent.interpret(followup_request())
    harness.house_view.chain.assert_awaited_once()
    saved: Trace = harness.traces.save.call_args.args[0]
    assert [step.name for step in saved.steps].count("house_view.chain") == 1


async def test_followup_chain_longer_than_limit_is_rejected(
    harness: Harness, rate: HouseViewClaim
) -> None:
    looped = deposit_trace(rate)
    harness.traces.find_by_card.return_value = looped.model_copy(
        update={
            "request": looped.request.model_copy(
                update={"action_context": FollowupContext(card_id="older-card", question="Ещё?")}
            )
        }
    )
    with pytest.raises(DomainError):
        await harness.agent.interpret(followup_request())
    limit = load_config(PLANS_PATH).max_followup_depth
    assert harness.traces.find_by_card.await_count == limit + 1
    harness.profiles.get_profile.assert_not_awaited()
    harness.llm.complete.assert_not_awaited()


def test_trace_news_builds_items_without_ref_kind(
    harness: Harness, rate: HouseViewClaim, monkeypatch: pytest.MonkeyPatch
) -> None:
    class StrictNews(NewsItem):
        model_config = ConfigDict(extra="forbid")

    monkeypatch.setattr(followup, "NewsItem", StrictNews)
    trace = deposit_trace(rate)
    assert trace.result is not None
    [item] = followup.trace_news(trace.result.cards[0])
    assert item.id == "rate-news"
