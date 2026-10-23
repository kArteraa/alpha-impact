import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from scripts.prefilter_mocks import make_seed
from shared.contracts.ports import Interpreter, LLMGateway, TraceStore
from shared.contracts.schemas import (
    DepositContext,
    Factor,
    InterpretRequest,
    LoanContext,
    Role,
    Trace,
)
from shared.di.container import Container
from tests.integration.test_prefilter_services import CLIENT, USER, persist
from tests.integration.test_prefilter_services import services as services


def first(sources: dict[str, dict[str, object]], prefix: str) -> str:
    return next(key for key in sorted(sources) if key.startswith(prefix))


@pytest.fixture
def model() -> AsyncMock:
    llm = AsyncMock(spec=LLMGateway)

    async def complete(
        task: str, system: str, user: str, schema: type[BaseModel]
    ) -> tuple[BaseModel, int, int, float]:
        context = json.loads(user)
        answer: dict[str, object]
        if task == "critic":
            answer = {"items": []}
        elif "template" in context:
            answer = {"focus": "Ставка банка и срок размещения", "tools": []}
        else:
            sources = context["context"]["sources"]
            rate = next(
                key
                for key, source in sorted(sources.items())
                if source["ref"]["kind"] == "house_view"
                and source["value"]["subject"] == "key_rate"
                and source["value"]["type"] == "forecast"
            )
            calc = [key for key in sources if key.startswith("calc:")]
            answer = {
                "headline": "Позиция банка по ставке меняет выбор срока",
                "what_happened": [
                    {
                        "text": "ЦБ сохранил ставку",
                        "type": "fact",
                        "source": first(sources, "news:"),
                    }
                ],
                "why_for_you": [
                    {"text": "Признак компании", "type": "ai", "source": first(sources, "profile:")}
                ],
                "consequences": [
                    {"text": "Итог расчёта", "type": "ai", "source": calc[0] if calc else rate}
                ],
                "actions": [
                    {"text": "Сравните сроки", "type": "ai", "source": first(sources, "profile:")}
                ],
                "bank_view": [{"text": sources[rate]["bank_text"], "type": "bank", "source": rate}],
                "significance": 0.6,
            }
        return schema.model_validate(answer), 200, 60, 0.0

    llm.complete.side_effect = complete
    return llm


def moment(action: DepositContext | LoanContext) -> InterpretRequest:
    return InterpretRequest(user_id=USER, client_id=CLIENT, role=Role.CFO, action_context=action)


@pytest.mark.parametrize(
    ("action", "kind"),
    [
        (DepositContext(amount=10_000_000, term_days=90), "deposit_terms"),
        (LoanContext(product="loan", amount=50_000_000, rate_type="floating"), "rate_burden"),
    ],
)
async def test_rate_moment_card_carries_calculation_from_seed_house_view(
    services: Container,
    sessions: async_sessionmaker[AsyncSession],
    model: AsyncMock,
    action: DepositContext | LoanContext,
    kind: str,
) -> None:
    news = (
        make_seed()
        .news[0]
        .model_copy(
            update={
                "id": "rate-news",
                "published_at": datetime.now(UTC),
                "entities": [f"product:{action.type}"],
                "factors": [
                    Factor(name="key_rate", direction="down", strength=1.0, horizon="year")
                ],
            }
        )
    )
    await persist(sessions, news)
    traces = AsyncMock(spec=TraceStore)
    services.register(LLMGateway, lambda _: model)
    services.register(TraceStore, lambda _: traces)
    response = await services.resolve(Interpreter).interpret(moment(action))
    card = response.cards[0]
    assert card.calculation is not None
    assert card.calculation.kind == kind
    assert card.calculation.formula
    assert card.calculation.assumptions
    assert card.consequences[0].source_ref.kind == "calc"
    assert card.bank_view[0].source_ref.kind == "house_view"
    assert not card.needs_review
    trace: Trace = traces.save.call_args.args[0]
    assert any(step.name == f"whatif.{kind}" for step in trace.steps)
    assert Trace.model_validate_json(trace.model_dump_json()).result == response
