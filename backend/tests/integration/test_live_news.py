import json
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from fastapi import FastAPI
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from apps.services.news.config import load_config as news_config
from apps.services.news.service import MANUAL_SOURCE, manual_id
from shared.contracts.ports import LLMGateway, TraceStore
from shared.contracts.schemas import ClaimType, InterpretResponse
from shared.db.models import NewsRow
from tests.integration.test_prefilter_services import CLIENT, USER, seed_client
from tests.news_data import KEY_RATE_ANSWER, unit

TITLE = "ЦБ снизил ключевую ставку до 16%"
BODY = "Банк России снизил ключевую ставку на 100 б.п., кредиты подешевеют."
PAGE_TEXT = f"{TITLE}\n{BODY}"
RATE_ANSWER = {**KEY_RATE_ANSWER, "products": ["loan"]}


class LiveNewsModel:
    def __init__(self) -> None:
        self.tasks: list[str] = []

    async def complete(
        self, task: str, system: str, user: str, schema: type | None = None
    ) -> tuple[object, int, int, float]:
        assert schema is not None and issubclass(schema, BaseModel)
        self.tasks.append(task)
        if task == news_config().llm_task:
            return schema.model_validate(RATE_ANSWER), 0, 0, 0.0
        if task == "critic":
            return schema.model_validate({"items": []}), 0, 0, 0.0
        if "tools" in schema.model_fields:
            return schema.model_validate({"focus": "Ставка и кредит", "tools": []}), 0, 0, 0.0
        return schema.model_validate(draft(json.loads(user)["context"]["sources"])), 0, 0, 0.0

    async def embed(self, text: str) -> list[float]:
        return unit(0)

    async def budget_left_rub(self) -> float:
        return 500.0


def draft(sources: dict[str, Any]) -> dict[str, object]:
    news = next(key for key in sources if key.startswith("news:"))
    profile = next(key for key in sources if key.startswith("profile:"))
    bank = next(key for key, value in sources.items() if value["ref"]["kind"] == "house_view")
    fact = [{"text": "Ставка снижена", "type": "fact", "source": news}]
    client = [{"text": "У компании есть кредит", "type": "fact", "source": profile}]
    return {
        "headline": "Ставка снижена — проверьте условия кредита",
        "what_happened": fact,
        "why_for_you": client,
        "consequences": fact,
        "actions": client,
        "bank_view": [{"text": sources[bank]["bank_text"], "type": "bank", "source": bank}],
        "significance": 0.8,
    }


@pytest.fixture
def model() -> LiveNewsModel:
    return LiveNewsModel()


@pytest.fixture
async def client(
    sessions: async_sessionmaker[AsyncSession], tmp_path: Path, model: LiveNewsModel
) -> AsyncIterator[httpx.AsyncClient]:
    from main import create_app

    await seed_client(sessions, tmp_path, "CL_PRODUCT_LOA_MARK")
    application: FastAPI = create_app()
    application.state.container.register(LLMGateway, lambda _: model)
    application.state.container.register(TraceStore, lambda _: AsyncMock(spec=TraceStore))
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as http:
        await http.post("/auth/mock", json={"user_id": USER})
        yield http
    await application.state.container.resolve(AsyncEngine).dispose()


async def interpret(http: httpx.AsyncClient, role: str) -> InterpretResponse:
    response = await http.post(
        "/interpret",
        json={
            "user_id": USER,
            "client_id": CLIENT,
            "role": role,
            "action_context": {"type": "page", "url": "", "text": PAGE_TEXT},
        },
    )
    assert response.status_code == 200, response.text
    return InterpretResponse.model_validate(response.json())


async def test_pasted_rate_news_gives_loan_client_card_with_bank_claim(
    client: httpx.AsyncClient,
    sessions: async_sessionmaker[AsyncSession],
    model: LiveNewsModel,
) -> None:
    response = await interpret(client, "cfo")

    assert not response.silent
    card = response.cards[0]
    assert card.what_happened[0].source_ref.id == manual_id(TITLE, BODY)
    assert card.bank_view
    assert all(claim.type == ClaimType.BANK for claim in card.bank_view)
    assert card.bank_view[0].source_ref.kind == "house_view"
    async with sessions() as session:
        [row] = (await session.scalars(select(NewsRow))).all()
    assert (row.id, row.source, row.factor_names) == (
        manual_id(TITLE, BODY),
        MANUAL_SOURCE,
        ["key_rate"],
    )
    assert model.tasks.count(news_config().llm_task) == 1


async def test_repeated_paste_comes_from_index(
    client: httpx.AsyncClient,
    sessions: async_sessionmaker[AsyncSession],
    model: LiveNewsModel,
) -> None:
    first = await interpret(client, "cfo")

    again = await interpret(client, "treasurer")

    assert not again.cached
    assert (
        again.cards[0].what_happened[0].source_ref.id
        == first.cards[0].what_happened[0].source_ref.id
    )
    assert model.tasks.count(news_config().llm_task) == 1
    async with sessions() as session:
        assert len((await session.scalars(select(NewsRow.id))).all()) == 1
