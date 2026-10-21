from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.llm.errors import ModelUnavailable
from apps.services.news.config import load_config
from apps.services.news.reannotate import reannotate_news
from apps.services.news.repository import add_news
from shared.contracts.errors import BudgetExceeded
from shared.contracts.schemas import Factor, NewsItem
from shared.db.models import NewsRow
from tests.news_data import EMPTY_ANSWER, NOW, TOKENS_IN, TOKENS_OUT, FakeNewsLlm, unit

CONFIG = load_config()
OLD_FACTOR = Factor(name="fx_rate", direction="up", strength=0.4, horizon="week")


def answer(**fields: Any) -> dict[str, Any]:
    return {**EMPTY_ANSWER, **fields}


async def index_old(sessions: async_sessionmaker[AsyncSession], *titles: str) -> None:
    async with sessions() as session, session.begin():
        for position, title in enumerate(titles):
            news = NewsItem(
                id=f"id-{position}",
                title=title,
                text=f"Текст: {title}",
                url=f"https://www.kommersant.ru/{position}",
                published_at=NOW - timedelta(hours=position),
                source="kommersant.ru",
                entities=["region:россия", "country:россия", "region:татарстан"],
                factors=[OLD_FACTOR],
            )
            await add_news(session, news, unit(position))


async def entities_of(sessions: async_sessionmaker[AsyncSession], title: str) -> list[str]:
    async with sessions() as session:
        row = await session.scalar(select(NewsRow).where(NewsRow.title == title))
    assert row is not None
    return row.entities


async def test_stored_news_get_vocabulary_entities_and_new_factors(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    await index_old(sessions, "Казань и Дубай")
    factor = {"name": "trade_logistics", "direction": "up", "strength": 0.7, "horizon": "month"}
    llm = FakeNewsLlm(
        answers={
            "Казань": answer(factors=[factor], regions=["Республика Татарстан"], countries=["ОАЭ"])
        }
    )

    result = await reannotate_news(sessions, llm, CONFIG)

    assert (result.updated, result.failed) == (1, ())
    assert (result.tokens_in, result.tokens_out) == (TOKENS_IN, TOKENS_OUT)
    assert llm.tasks == [CONFIG.llm_task]
    assert await entities_of(sessions, "Казань и Дубай") == [
        "region:республика татарстан",
        "country:ae",
    ]
    async with sessions() as session:
        row = await session.scalar(select(NewsRow))
    assert row is not None
    assert row.factor_names == ["trade_logistics"]
    assert row.factors == [factor]


async def test_model_error_keeps_old_annotation_and_the_run(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    await index_old(sessions, "Сбойная", "Нормальная")
    llm = FakeNewsLlm(errors={"Сбойная": ModelUnavailable("x")})

    result = await reannotate_news(sessions, llm, CONFIG)

    assert (result.updated, result.failed) == (1, ("https://www.kommersant.ru/0",))
    assert "region:россия" in await entities_of(sessions, "Сбойная")
    assert await entities_of(sessions, "Нормальная") == []


async def test_exhausted_budget_stops_reannotation(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    await index_old(sessions, "Первая", "Вторая")
    llm = FakeNewsLlm(errors={"Первая": BudgetExceeded("spent")})

    with pytest.raises(BudgetExceeded):
        await reannotate_news(sessions, llm, CONFIG)

    assert "region:россия" in await entities_of(sessions, "Первая")
