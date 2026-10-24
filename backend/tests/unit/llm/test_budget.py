from datetime import timedelta

import pytest

from shared.contracts.errors import BudgetExceeded
from tests.unit.conftest import SETTINGS_ENV
from tests.unit.llm.fakes import TODAY, VECTOR, MemoryStore, ModelServer, Usage, make_gateway


def spent(store: MemoryStore, cost_rub: float, days_ago: int = 0) -> None:
    store.add(
        Usage(
            day=TODAY - timedelta(days=days_ago),
            task="interpret",
            model="z-ai/glm-5.3-flash",
            tokens_in=0,
            tokens_out=0,
            cost_rub=cost_rub,
        )
    )


async def test_fresh_day_leaves_budget_minus_reserve() -> None:
    gateway = make_gateway(ModelServer().http_client(), MemoryStore())
    assert await gateway.budget_left_rub() == pytest.approx(450.0)


async def test_call_is_charged_by_the_cost_in_the_answer() -> None:
    store = MemoryStore()
    gateway = make_gateway(ModelServer(cost_rub=0.25).http_client(), store)
    await gateway.complete("interpret", "system", "user")
    assert store.usages[0].cost_rub == pytest.approx(0.25)
    assert store.usages[0].model == SETTINGS_ENV["MODEL_INTERPRET"]
    assert store.usages[0].task == "interpret"
    assert store.usages[0].day == TODAY
    assert await gateway.budget_left_rub() == pytest.approx(449.75)


async def test_exhausted_budget_raises_without_calling_model() -> None:
    server = ModelServer()
    store = MemoryStore()
    spent(store, 450.0)
    with pytest.raises(BudgetExceeded):
        await make_gateway(server.http_client(), store).complete("interpret", "system", "user")
    assert server.requests == []


async def test_reserve_is_never_spent() -> None:
    store = MemoryStore()
    spent(store, 460.0)
    gateway = make_gateway(ModelServer().http_client(), store)
    assert await gateway.budget_left_rub() == 0.0
    with pytest.raises(BudgetExceeded):
        await gateway.complete("interpret", "system", "user")


async def test_exhausted_budget_does_not_block_embeddings() -> None:
    store = MemoryStore()
    spent(store, 450.0)
    assert await make_gateway(ModelServer().http_client(), store).embed("text") == VECTOR
    assert len(store.usages) == 1


async def test_cache_still_answers_when_budget_is_exhausted() -> None:
    server = ModelServer(content="cached answer")
    store = MemoryStore()
    gateway = make_gateway(server.http_client(), store)
    await gateway.complete("interpret", "system", "user")
    spent(store, 450.0)
    assert await gateway.complete("interpret", "system", "user") == ("cached answer", 0, 0, 0.0)
    assert len(server.requests) == 1


async def test_yesterday_spending_does_not_count() -> None:
    store = MemoryStore()
    spent(store, 450.0, days_ago=1)
    assert await make_gateway(
        ModelServer().http_client(), store
    ).budget_left_rub() == pytest.approx(450.0)


async def test_reserve_share_comes_from_configuration() -> None:
    gateway = make_gateway(
        ModelServer().http_client(), MemoryStore(), daily_budget_rub=100.0, reserve_share=0.2
    )
    assert await gateway.budget_left_rub() == pytest.approx(80.0)
