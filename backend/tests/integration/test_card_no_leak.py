from collections.abc import AsyncIterator
from datetime import UTC, date, datetime

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from apps.services.counterparty.batch import rebuild_graph
from apps.services.house_view.batch import load_house_view
from apps.services.house_view.ingest.config import load_config as house_view_config
from apps.services.news.repository import add_news
from apps.services.profile.batch import rebuild_profiles
from apps.services.profile.config import load_config as load_profile_config
from scripts.seed import RAW_DIR, seed_users
from shared.config.embedding import EMBEDDING_DIMENSION
from shared.config.factors import FACTORS
from shared.config.industries import INDUSTRIES
from shared.config.news_entities import INDUSTRY, PRODUCT, PRODUCTS, entity
from shared.contracts.ports import LLMGateway, TraceStore
from shared.contracts.schemas import Factor, InsightCard, InterpretResponse, NewsItem, Trace
from tests.house_view_data import APPROVED_FILE
from tests.leak import (
    CONFIG,
    PAYMENTS_FILE,
    assert_no_foreign_data,
    probes,
    seed_clients,
    seed_foreign_data,
)

PAYMENT_AMOUNT = 1_234_567.89
VECTOR = [1.0, *([0.0] * (EMBEDDING_DIMENSION - 1))]
NEWS_ID = "leak-probe-news"
OWN_INPUT = frozenset({"request"})
CARD_PROBES = 25


class EchoModel:
    async def complete(
        self, task: str, system: str, user: str, schema: type | None = None
    ) -> tuple[object, int, int]:
        assert schema is not None and issubclass(schema, BaseModel)
        if "items" in schema.model_fields:
            return schema.model_validate({"items": []}), 0, 0
        if "tools" in schema.model_fields:
            return schema.model_validate({"focus": user, "tools": []}), 0, 0
        echo = [{"text": user, "type": "ai", "source": f"news:{NEWS_ID}"}]
        answer = {
            "headline": user,
            "what_happened": echo,
            "why_for_you": echo,
            "consequences": echo,
            "actions": echo,
            "bank_view": [],
            "significance": 0.5,
        }
        return schema.model_validate(answer), 0, 0

    async def embed(self, text: str) -> list[float]:
        return VECTOR


class MemoryTraces:
    def __init__(self) -> None:
        self.saved: dict[str, Trace] = {}

    async def save(self, trace: Trace) -> None:
        self.saved[trace.id] = trace

    async def get(self, trace_id: str) -> Trace | None:
        return self.saved.get(trace_id)

    async def metrics(self, since: date) -> dict[str, float]:
        return {}


def probe_news() -> NewsItem:
    industries = (entity(INDUSTRY, name) for name in sorted(set(INDUSTRIES.values())))
    products = (entity(PRODUCT, name) for name in PRODUCTS)
    return NewsItem(
        id=NEWS_ID,
        title="Синтетическая новость для проверки утечек",
        text="Новость касается всех отраслей и продуктов, чтобы агент не молчал",
        url="https://example.invalid/leak-probe-news",
        published_at=datetime.now(UTC),
        source="synthetic",
        entities=sorted({name for name in (*industries, *products) if name}),
        factors=[
            Factor(name=name, direction="up", strength=1.0, horizon="month") for name in FACTORS
        ],
    )


def sourced(card: InsightCard) -> bool:
    claims = [
        *card.what_happened,
        *card.why_for_you,
        *card.consequences,
        *card.actions,
        *card.bank_view,
    ]
    return bool(claims) and all(claim.source_ref in card.basis for claim in claims)


@pytest.fixture
def traces() -> MemoryTraces:
    return MemoryTraces()


@pytest.fixture
async def app(
    sessions: async_sessionmaker[AsyncSession], traces: MemoryTraces
) -> AsyncIterator[FastAPI]:
    from main import create_app

    await seed_users(sessions)
    await rebuild_profiles(sessions, RAW_DIR, load_profile_config())
    await rebuild_graph(sessions, RAW_DIR, CONFIG)
    await load_house_view(sessions, APPROVED_FILE, house_view_config().expired_docs)
    async with sessions() as session, session.begin():
        assert await add_news(session, probe_news(), VECTOR)
    application = create_app()
    application.state.container.register(LLMGateway, lambda _: EchoModel())
    application.state.container.register(TraceStore, lambda _: traces)
    yield application
    await application.state.container.resolve(AsyncEngine).dispose()


@pytest.mark.skipif(not PAYMENTS_FILE.exists(), reason="data/raw is not present")
async def test_seed_cards_contain_no_foreign_data(app: FastAPI, traces: MemoryTraces) -> None:
    users = seed_clients()
    assert all(PAYMENT_AMOUNT not in foreign.amounts for foreign in seed_foreign_data().values())
    cards = 0
    transport = httpx.ASGITransport(app=app)
    for client_id, foreign in seed_foreign_data().items():
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            login = await client.post("/auth/mock", json={"user_id": users[client_id]})
            assert login.status_code == 200
            for beneficiary_id, inn in probes(foreign, CARD_PROBES):
                reply = await client.post(
                    "/interpret",
                    json={
                        "user_id": users[client_id],
                        "client_id": client_id,
                        "role": "cfo",
                        "action_context": {
                            "type": "payment",
                            "beneficiary_id": beneficiary_id,
                            "inn": inn,
                            "amount": PAYMENT_AMOUNT,
                        },
                    },
                )
                assert reply.status_code == 200, reply.text
                response = InterpretResponse.model_validate(reply.json())
                assert response.silent != bool(response.cards)
                assert all(sourced(card) for card in response.cards)
                assert_no_foreign_data(response, client_id, foreign)
                cards += len(response.cards)
        for trace in traces.saved.values():
            if trace.request.client_id == client_id:
                assert_no_foreign_data(trace, client_id, foreign, OWN_INPUT)
    assert cards
    assert traces.saved
