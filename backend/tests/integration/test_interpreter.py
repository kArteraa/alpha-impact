import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scripts.prefilter_mocks import make_seed
from shared.contracts.errors import AccessDenied
from shared.contracts.ports import Interpreter, LLMGateway, TraceStore
from shared.contracts.schemas import InterpretRequest, PaymentContext, Role, Trace
from shared.di.container import Container
from tests.integration.test_prefilter_services import CLIENT, LOGISTICS, STATIONERY, USER, persist
from tests.integration.test_prefilter_services import services as services
from tests.unit.interpreter.support import draft_answer


@pytest.fixture
def model() -> AsyncMock:
    llm = AsyncMock(spec=LLMGateway)

    async def complete(
        task: str, system: str, user: str, schema: type[BaseModel]
    ) -> tuple[BaseModel, int, int]:
        context = json.loads(user)
        answer: dict[str, object]
        if task == "critic":
            answer = {"items": []}
        elif "template" in context:
            answer = {
                "focus": "Уточнить сроки и тариф перевозчика",
                "tools": [{"tool": "house_view.claims", "argument": "trade_logistics"}],
            }
        else:
            answer = draft_answer()
            house_view = [
                (key, source)
                for key, source in context["context"]["sources"].items()
                if source["ref"]["kind"] == "house_view"
            ]
            assert house_view
            key, source = house_view[0]
            answer["bank_view"] = [{"text": source["bank_text"], "type": "bank", "source": key}]
        return schema.model_validate(answer), 200, 60

    llm.complete.side_effect = complete
    return llm


def request(beneficiary: str, user: str) -> InterpretRequest:
    return InterpretRequest(
        user_id=user,
        client_id=CLIENT,
        role=Role.CFO,
        action_context=PaymentContext(amount=100_000, beneficiary_id=beneficiary),
    )


async def test_interpreter_end_to_end_through_di(
    services: Container, sessions: async_sessionmaker[AsyncSession], model: AsyncMock
) -> None:
    news = make_seed().news[0].model_copy(update={"published_at": datetime.now(UTC)})
    await persist(sessions, news)
    traces = AsyncMock(spec=TraceStore)
    services.register(LLMGateway, lambda _: model)
    services.register(TraceStore, lambda _: traces)
    agent = services.resolve(Interpreter)
    relevant = await agent.interpret(request(LOGISTICS, USER))
    assert not relevant.silent
    card = relevant.cards[0]
    assert card.what_happened[0].source_ref.id == news.id
    assert card.bank_view[0].source_ref.kind == "house_view"
    assert not card.needs_review
    trace: Trace = traces.save.call_args.args[0]
    assert Trace.model_validate_json(trace.model_dump_json()).result == relevant
    assert trace.id == card.trace_id
    assert any(step.step == "plan" for step in trace.steps)
    assert any(step.name == "house_view.claims" for step in trace.steps)
    assert trace.critic_verdicts == ["1: ok"]
    assert len(card.basis) >= 3
    assert all(
        claim.source_ref in card.basis
        for block in (
            card.what_happened,
            card.why_for_you,
            card.consequences,
            card.actions,
            card.bank_view,
        )
        for claim in block
    )
    calls = model.complete.await_count
    irrelevant = await agent.interpret(request(STATIONERY, USER))
    assert irrelevant.silent and not irrelevant.cards
    assert model.complete.await_count == calls
    assert traces.save.await_count == 2


async def test_real_profile_authorization_blocks_interpreter(
    services: Container, model: AsyncMock
) -> None:
    traces = AsyncMock(spec=TraceStore)
    services.register(LLMGateway, lambda _: model)
    services.register(TraceStore, lambda _: traces)
    with pytest.raises(AccessDenied):
        await services.resolve(Interpreter).interpret(request(LOGISTICS, "another-user"))
    model.complete.assert_not_awaited()
    assert traces.save.call_args.args[0].result is None


async def test_interpreter_trace_is_stored_and_read_back(
    services: Container, sessions: async_sessionmaker[AsyncSession], model: AsyncMock
) -> None:
    news = make_seed().news[0].model_copy(update={"published_at": datetime.now(UTC)})
    await persist(sessions, news)
    services.register(LLMGateway, lambda _: model)
    card = (await services.resolve(Interpreter).interpret(request(LOGISTICS, USER))).cards[0]
    stored = await services.resolve(TraceStore).get(card.trace_id)
    assert stored is not None
    steps = {step.name: step for step in stored.steps}
    assert [step.step for step in stored.steps][-1] == "final"
    assert "Уточнить сроки и тариф перевозчика" in steps["plan"].output_summary
    assert steps["house_view.claims"].input_summary == "trade_logistics"
    assert "trade_logistics" in steps["house_view.claims"].output_summary
    assert "industry_class" in steps["counterparty.context"].output_summary
    assert str(draft_answer()["headline"]) in steps["draft"].output_summary
    assert stored.critic_verdicts == ["1: ok"]
    assert stored.result is not None and stored.result.cards == [card]
