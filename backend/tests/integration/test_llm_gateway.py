import asyncio
from collections.abc import Callable
from datetime import timedelta
from typing import Any

import httpx
import pytest
from fastapi import FastAPI, Header
from pydantic import BaseModel
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.llm import utc_today
from apps.services.llm.catalog import MODELS_PATH, load_models
from apps.services.llm.service import ModelGateway
from apps.services.llm.store import SqlUsageStore
from shared.contracts.errors import BudgetExceeded
from shared.db.models import LlmCacheRow, LlmUsageRow
from tests.unit.llm import fakes

CACHE_TTL_SECONDS = 3600


class Factor(BaseModel):
    name: str
    strength: float


class MockModelServer:
    def __init__(self, delay_seconds: float = 0.0) -> None:
        self.calls = 0
        self.bodies: list[dict[str, Any]] = []
        self.delay_seconds = delay_seconds
        self.app = FastAPI()
        self.app.post("/v1/chat/completions")(self.chat)

    async def chat(self, body: dict[str, Any], authorization: str = Header()) -> dict[str, Any]:
        assert authorization == "Bearer test-key"
        self.calls += 1
        self.bodies.append(body)
        await asyncio.sleep(self.delay_seconds)
        return {
            "choices": [{"message": {"content": '{"name": "key_rate", "strength": 0.8}'}}],
            "usage": {"prompt_tokens": 2000, "completion_tokens": 400, "cost": 0.05},
        }

    def http_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            transport=httpx.ASGITransport(app=self.app),
            base_url="http://llm.test/v1",
            headers={"Authorization": "Bearer test-key"},
        )


@pytest.fixture
def server() -> MockModelServer:
    return MockModelServer()


@pytest.fixture
def embedder() -> fakes.CountingEmbedder:
    return fakes.CountingEmbedder()


@pytest.fixture
def make_gateway(
    server: MockModelServer,
    embedder: fakes.CountingEmbedder,
    sessions: async_sessionmaker[AsyncSession],
) -> Callable[..., ModelGateway]:
    def build(daily_budget_rub: float = 500.0) -> ModelGateway:
        models = load_models(MODELS_PATH)
        return fakes.make_gateway(
            server.http_client(),
            SqlUsageStore(sessions, CACHE_TTL_SECONDS),
            daily_budget_rub=daily_budget_rub,
            allowed=models.models,
            reasoning_off=models.reasoning_off_tasks,
            today=utc_today,
            embedder=embedder,
        )

    return build


async def test_followup_without_reasoning_validates_accounts_and_caches(
    make_gateway: Callable[..., ModelGateway],
    server: MockModelServer,
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    result = await make_gateway().complete("followup", "sys", "usr", Factor)
    assert result == (Factor(name="key_rate", strength=0.8), 2000, 400, 0.05)
    assert server.bodies[0]["model"] == "qwen/qwen3.6-35b-a3b"
    assert server.bodies[0]["reasoning"] == {"enabled": False}
    assert server.bodies[0]["response_format"]["type"] == "json_schema"
    async with sessions() as session:
        usage = (await session.scalars(select(LlmUsageRow))).one()
        assert await session.scalar(select(func.count()).select_from(LlmCacheRow)) == 1
    assert (usage.task, usage.model, usage.tokens_in, usage.tokens_out) == (
        "followup",
        "qwen/qwen3.6-35b-a3b",
        2000,
        400,
    )
    assert float(usage.cost_rub) == pytest.approx(0.05)
    assert await make_gateway().complete("followup", "sys", "usr", Factor) == (
        Factor(name="key_rate", strength=0.8),
        0,
        0,
        0.0,
    )
    assert server.calls == 1
    assert await make_gateway().budget_left_rub() == pytest.approx(449.95)


async def test_structured_call_is_recorded_in_usage(
    make_gateway: Callable[..., ModelGateway], sessions: async_sessionmaker[AsyncSession]
) -> None:
    gateway = make_gateway()
    result = await gateway.complete("interpret", "sys", "usr", Factor)
    assert result == (Factor(name="key_rate", strength=0.8), 2000, 400, 0.05)
    async with sessions() as session:
        usage = (await session.scalars(select(LlmUsageRow))).one()
    assert (usage.task, usage.model, usage.tokens_in, usage.tokens_out) == (
        "interpret",
        "z-ai/glm-5.3-flash",
        2000,
        400,
    )
    assert float(usage.cost_rub) == pytest.approx(0.05)
    assert await gateway.budget_left_rub() == pytest.approx(449.95)


async def test_charged_answer_without_token_counts_keeps_its_cost(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    store = SqlUsageStore(sessions, CACHE_TTL_SECONDS)
    reservation = await store.reserve(utc_today(), "interpret", "z-ai/glm-5.3-flash", 1.0, 450.0)
    assert reservation is not None
    await store.settle(reservation, 0, 0, 0.02)
    async with sessions() as session:
        row = (await session.scalars(select(LlmUsageRow))).one()
    assert float(row.cost_rub) == pytest.approx(0.02)


async def test_cache_survives_a_new_gateway_instance(
    make_gateway: Callable[..., ModelGateway],
    server: MockModelServer,
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    await make_gateway().complete("interpret", "sys", "usr", Factor)
    result = await make_gateway().complete("interpret", "sys", "usr", Factor)
    assert result == (Factor(name="key_rate", strength=0.8), 0, 0, 0.0)
    assert server.calls == 1
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(LlmCacheRow)) == 1


async def test_spending_is_shared_between_instances(
    make_gateway: Callable[..., ModelGateway],
) -> None:
    first = make_gateway()
    await first.complete("interpret", "sys", "usr")
    assert await make_gateway().budget_left_rub() == await first.budget_left_rub()
    assert await first.budget_left_rub() < 450.0


async def test_exhausted_budget_raises(
    make_gateway: Callable[..., ModelGateway], server: MockModelServer
) -> None:
    gateway = make_gateway(daily_budget_rub=0.0)
    with pytest.raises(BudgetExceeded):
        await gateway.complete("interpret", "sys", "usr")
    assert server.calls == 0


async def test_embedding_is_cached_in_database(
    make_gateway: Callable[..., ModelGateway], embedder: fakes.CountingEmbedder
) -> None:
    assert await make_gateway().embed("ставка") == fakes.VECTOR
    assert await make_gateway().embed("ставка") == fakes.VECTOR
    assert embedder.calls == ["ставка"]


async def test_embedding_spends_no_budget(
    make_gateway: Callable[..., ModelGateway], sessions: async_sessionmaker[AsyncSession]
) -> None:
    gateway = make_gateway()
    await gateway.embed("ставка")
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(LlmUsageRow)) == 0
    assert await gateway.budget_left_rub() == pytest.approx(450.0)


async def age_cache(sessions: async_sessionmaker[AsyncSession], seconds: int) -> None:
    aged = func.now() - timedelta(seconds=seconds)
    async with sessions() as session, session.begin():
        await session.execute(update(LlmCacheRow).values(created_at=aged))


async def test_concurrent_calls_share_one_reservation_across_gateways(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    server = MockModelServer(delay_seconds=0.2)
    async with sessions() as session, session.begin():
        session.add(
            LlmUsageRow(
                day=utc_today(),
                task="interpret",
                model="z-ai/glm-5.3-flash",
                tokens_in=0,
                tokens_out=0,
                cost_rub=449.5,
            )
        )
    gateways = [
        fakes.make_gateway(
            server.http_client(),
            SqlUsageStore(sessions, CACHE_TTL_SECONDS),
            allowed=load_models(MODELS_PATH).models,
            today=utc_today,
        )
        for _ in range(5)
    ]
    results = await asyncio.gather(
        *(gateway.complete("interpret", "sys", f"usr {n}") for n, gateway in enumerate(gateways)),
        return_exceptions=True,
    )
    assert sum(not isinstance(result, BaseException) for result in results) == 1
    assert sum(isinstance(result, BudgetExceeded) for result in results) == 4
    assert server.calls == 1


async def test_expired_cache_entry_is_a_miss_and_is_refreshed(
    make_gateway: Callable[..., ModelGateway],
    server: MockModelServer,
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    gateway = make_gateway()
    await gateway.complete("interpret", "sys", "usr", Factor)
    await age_cache(sessions, CACHE_TTL_SECONDS + 60)
    result = await gateway.complete("interpret", "sys", "usr", Factor)
    assert result == (Factor(name="key_rate", strength=0.8), 2000, 400, 0.05)
    assert server.calls == 2
    assert await gateway.complete("interpret", "sys", "usr", Factor) == (
        Factor(name="key_rate", strength=0.8),
        0,
        0,
        0.0,
    )
    assert server.calls == 2


async def test_fresh_cache_entry_is_still_a_hit(
    make_gateway: Callable[..., ModelGateway],
    embedder: fakes.CountingEmbedder,
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    gateway = make_gateway()
    await gateway.embed("ставка")
    await age_cache(sessions, CACHE_TTL_SECONDS - 60)
    assert await gateway.embed("ставка") == fakes.VECTOR
    assert embedder.calls == ["ставка"]


async def test_writing_to_cache_drops_other_expired_entries(
    make_gateway: Callable[..., ModelGateway], sessions: async_sessionmaker[AsyncSession]
) -> None:
    gateway = make_gateway()
    await gateway.embed("старый текст")
    await age_cache(sessions, CACHE_TTL_SECONDS + 60)
    await gateway.embed("новый текст")
    async with sessions() as session:
        assert await session.scalar(select(func.count()).select_from(LlmCacheRow)) == 1
