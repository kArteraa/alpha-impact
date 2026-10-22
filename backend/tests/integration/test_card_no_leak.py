import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from apps.services.counterparty.batch import rebuild_graph
from apps.services.house_view.batch import load_house_view
from apps.services.house_view.ingest.config import load_config as house_view_config
from apps.services.profile.batch import rebuild_profiles
from apps.services.profile.config import load_config as load_profile_config
from scripts.prefilter_mocks import make_seed
from scripts.seed import RAW_DIR, seed_users
from shared.config.factors import FACTORS
from shared.config.industries import INDUSTRIES
from shared.config.news_entities import INDUSTRY, PRODUCT, PRODUCTS, entity
from shared.contracts.ports import LLMGateway, TraceStore
from shared.contracts.schemas import Factor, InterpretResponse, NewsItem, Trace
from tests.house_view_data import APPROVED_FILE
from tests.integration.test_prefilter_services import persist
from tests.leak import (
    CONFIG,
    PAYMENTS_FILE,
    assert_no_foreign_data,
    probes,
    seed_clients,
    seed_foreign_data,
)

PAYMENT_AMOUNT = 1_234_567.89
NEWS_ID = "leak-probe-news"
CARD_PROBES = 25
OTHER_ACTIONS: list[dict[str, object]] = [
    {"type": "dashboard"},
    {"type": "deposit", "amount": PAYMENT_AMOUNT, "term_days": 90},
    {"type": "fx", "currency": "CNY", "amount": PAYMENT_AMOUNT},
    {"type": "loan", "product": "loan", "amount": PAYMENT_AMOUNT},
    {"type": "payroll", "amount": PAYMENT_AMOUNT},
]


class EchoModel:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    async def complete(
        self, task: str, system: str, user: str, schema: type | None = None
    ) -> tuple[object, int, int]:
        assert schema is not None and issubclass(schema, BaseModel)
        self.prompts += [system, user]
        if task == "critic":
            return schema.model_validate({"items": []}), 0, 0
        if "tools" in schema.model_fields:
            return schema.model_validate({"focus": user, "tools": []}), 0, 0
        sources = json.loads(user)["context"]["sources"]
        client_facts = [key for key in sources if key.startswith(("profile:", "graph:"))][:1]
        echo = [
            {"text": user, "type": "ai", "source": source}
            for source in (f"news:{NEWS_ID}", *client_facts)
        ]
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


def probe_news() -> NewsItem:
    industries = (entity(INDUSTRY, name) for name in INDUSTRIES.values())
    products = (entity(PRODUCT, name) for name in PRODUCTS)
    return (
        make_seed()
        .news[0]
        .model_copy(
            update={
                "id": NEWS_ID,
                "published_at": datetime.now(UTC),
                "entities": sorted({name for name in (*industries, *products) if name}),
                "factors": [
                    Factor(name=name, direction="up", strength=1.0, horizon="month")
                    for name in FACTORS
                ],
            }
        )
    )


@pytest.fixture
def model() -> EchoModel:
    return EchoModel()


@pytest.fixture
def traces() -> AsyncMock:
    return AsyncMock(spec=TraceStore)


@pytest.fixture
async def app(
    sessions: async_sessionmaker[AsyncSession], model: EchoModel, traces: AsyncMock
) -> AsyncIterator[FastAPI]:
    from main import create_app

    await seed_users(sessions)
    await rebuild_profiles(sessions, RAW_DIR, load_profile_config())
    await rebuild_graph(sessions, RAW_DIR, CONFIG)
    await load_house_view(sessions, APPROVED_FILE, house_view_config().expired_docs)
    await persist(sessions, probe_news())
    application = create_app()
    application.state.container.register(LLMGateway, lambda _: model)
    application.state.container.register(TraceStore, lambda _: traces)
    yield application
    await application.state.container.resolve(AsyncEngine).dispose()


@pytest.mark.skipif(not PAYMENTS_FILE.exists(), reason="data/raw is not present")
async def test_seed_cards_contain_no_foreign_data(
    app: FastAPI, model: EchoModel, traces: AsyncMock
) -> None:
    users = seed_clients()
    foreign_data = seed_foreign_data()
    assert not any(foreign.has_amount(PAYMENT_AMOUNT) for foreign in foreign_data.values())
    cards = 0
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for client_id, foreign in foreign_data.items():
            user_id = users[client_id]
            assert (await client.post("/auth/mock", json={"user_id": user_id})).status_code == 200
            model.prompts.clear()
            payments: list[dict[str, object]] = [
                {
                    "type": "payment",
                    "beneficiary_id": beneficiary_id,
                    "inn": inn,
                    "amount": PAYMENT_AMOUNT,
                }
                for beneficiary_id, inn in probes(foreign, CARD_PROBES)
            ]
            for action in [*payments, *OTHER_ACTIONS]:
                reply = await client.post(
                    "/interpret",
                    json={
                        "user_id": user_id,
                        "client_id": client_id,
                        "role": "cfo",
                        "action_context": action,
                    },
                )
                assert reply.status_code == 200, reply.text
                response = InterpretResponse.model_validate(reply.json())
                assert response.silent != bool(response.cards)
                assert_no_foreign_data(response, client_id, foreign)
                cards += len(response.cards)
            assert model.prompts
            assert_no_foreign_data(model.prompts, client_id, foreign)
    saved: list[Trace] = [call.args[0] for call in traces.save.call_args_list]
    for trace in saved:
        owner = trace.request.client_id
        dumped = trace.model_dump(
            mode="json",
            exclude={"result": True, "request": {"action_context": {"beneficiary_id", "inn"}}},
        )
        assert_no_foreign_data(dumped, owner, foreign_data[owner])
    assert cards
    assert saved
