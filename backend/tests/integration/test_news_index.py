from datetime import timedelta
from typing import Any

import httpx
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.llm.errors import ModelUnavailable
from apps.services.news.annotation import annotation_schema, to_news_item
from apps.services.news.config import load_config
from apps.services.news.feed import FeedEntry
from apps.services.news.ingest import IngestResult, ingest_news
from apps.services.news.repository import add_news
from apps.services.news.service import NewsIndex
from shared.config.embedding import EMBEDDING_DIMENSION
from shared.contracts.errors import BudgetExceeded
from shared.db.models import NewsRow
from tests.news_data import (
    EMPTY_ANSWER,
    KEY_RATE_ANSWER,
    NOW,
    TOKENS_IN,
    TOKENS_OUT,
    FakeNewsLlm,
    item,
    near,
    rss,
    unit,
)

CONFIG = load_config()
SCHEMA = annotation_schema(CONFIG)
KOMMERSANT = "https://www.kommersant.ru/rss/section-economics.xml"
VEDOMOSTI = "https://www.vedomosti.ru/rss/rubric/economics"
SINCE = (NOW - timedelta(days=14)).date()


def factor(name: str, strength: float) -> dict[str, Any]:
    return {"name": name, "direction": "up", "strength": strength, "horizon": "month"}


def answer(**fields: Any) -> dict[str, Any]:
    return {**EMPTY_ANSWER, **fields}


def transport(feeds: dict[str, bytes | int]) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        body = feeds[str(request.url)]
        if isinstance(body, int):
            return httpx.Response(body)
        return httpx.Response(200, content=body)

    return httpx.MockTransport(handler)


async def ingest(
    sessions: async_sessionmaker[AsyncSession], llm: FakeNewsLlm, feeds: dict[str, bytes | int]
) -> IngestResult:
    async with httpx.AsyncClient(transport=transport(feeds)) as http:
        return await ingest_news(sessions, llm, http, list(feeds), CONFIG, NOW)


async def stored(sessions: async_sessionmaker[AsyncSession]) -> list[str]:
    async with sessions() as session:
        return list((await session.scalars(select(NewsRow.title).order_by(NewsRow.title))).all())


async def test_fresh_news_are_annotated_and_stored(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm(answers={"Ставка": KEY_RATE_ANSWER})
    feed = rss(
        item("Ставка снижена до 16%", "https://www.kommersant.ru/doc/1", NOW, "ЦБ снизил ставку"),
        item("Склады дорожают", "https://www.kommersant.ru/doc/2", NOW - timedelta(days=13)),
        item("Старая новость", "https://www.kommersant.ru/doc/3", NOW - timedelta(days=15)),
    )

    result = await ingest(sessions, llm, {KOMMERSANT: feed})

    assert (result.added, result.duplicates, result.total) == (2, 0, 2)
    assert (result.tokens_in, result.tokens_out) == (2 * TOKENS_IN, 2 * TOKENS_OUT)
    assert await stored(sessions) == ["Склады дорожают", "Ставка снижена до 16%"]
    async with sessions() as session:
        row = await session.scalar(select(NewsRow).where(NewsRow.title.startswith("Ставка")))
    assert row is not None
    assert row.source == "kommersant.ru"
    assert row.text == "ЦБ снизил ставку"
    assert row.factor_names == ["key_rate"]
    assert "region:москва" in row.entities
    assert len(row.embedding) == EMBEDDING_DIMENSION


async def test_same_title_in_another_feed_is_not_embedded_or_annotated(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm()
    feeds: dict[str, bytes | int] = {
        KOMMERSANT: rss(item("ЦБ снизил ставку", "https://www.kommersant.ru/doc/1", NOW)),
        VEDOMOSTI: rss(item("ЦБ  снизил ставку", "https://www.vedomosti.ru/1", NOW)),
    }

    result = await ingest(sessions, llm, feeds)

    assert result.added == 1
    assert len(llm.embedded) == len(llm.completions) == 1


async def test_close_news_with_same_numbers_is_a_duplicate(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm(vectors={"MOL выкупил": unit(0), "Венгерская MOL": near(0, 1)})
    feeds: dict[str, bytes | int] = {
        KOMMERSANT: rss(item("MOL выкупил долю NIS за 1 млрд", "https://www.kommersant.ru/1", NOW)),
        VEDOMOSTI: rss(
            item("Венгерская MOL купила долю NIS за 1 млрд", "https://www.vedomosti.ru/1", NOW)
        ),
    }

    result = await ingest(sessions, llm, feeds)

    assert (result.added, result.duplicates) == (1, 1)
    assert len(llm.completions) == 1


async def test_close_news_with_other_numbers_are_both_kept(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm(vectors={"до 16%": unit(0), "до 17%": near(0, 1)})
    feeds: dict[str, bytes | int] = {
        KOMMERSANT: rss(item("ЦБ снизил ставку до 16%", "https://www.kommersant.ru/1", NOW)),
        VEDOMOSTI: rss(item("ЦБ понизил ставку до 17%", "https://www.vedomosti.ru/1", NOW)),
    }

    result = await ingest(sessions, llm, feeds)

    assert (result.added, result.duplicates) == (2, 0)


async def test_close_news_outside_time_window_are_both_kept(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    later = NOW - timedelta(hours=CONFIG.dedup_window_hours + 1)
    llm = FakeNewsLlm(vectors={"сохранил курс": unit(0), "держит курс": near(0, 1)})
    feeds: dict[str, bytes | int] = {
        KOMMERSANT: rss(item("ЦБ сохранил курс доллара", "https://www.kommersant.ru/1", NOW)),
        VEDOMOSTI: rss(item("ЦБ держит курс доллара", "https://www.vedomosti.ru/1", later)),
    }

    result = await ingest(sessions, llm, feeds)

    assert (result.added, result.duplicates) == (2, 0)


async def test_repeated_run_calls_no_model(sessions: async_sessionmaker[AsyncSession]) -> None:
    feeds: dict[str, bytes | int] = {
        KOMMERSANT: rss(
            item("Первая", "https://www.kommersant.ru/1", NOW),
            item("Вторая", "https://www.kommersant.ru/2", NOW),
        )
    }
    await ingest(sessions, FakeNewsLlm(), feeds)
    llm = FakeNewsLlm()

    result = await ingest(sessions, llm, feeds)

    assert (result.added, result.total) == (0, 2)
    assert llm.completions == llm.embedded == []


async def test_model_error_skips_news_until_next_run(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    feeds: dict[str, bytes | int] = {
        KOMMERSANT: rss(
            item("Сбойная", "https://www.kommersant.ru/1", NOW),
            item("Нормальная", "https://www.kommersant.ru/2", NOW),
        )
    }

    first = await ingest(sessions, FakeNewsLlm(errors={"Сбойная": ModelUnavailable("x")}), feeds)
    second = await ingest(sessions, FakeNewsLlm(), feeds)

    assert (first.added, first.failed) == (1, ("https://www.kommersant.ru/1",))
    assert (second.added, second.failed, second.total) == (1, (), 2)


async def test_exhausted_budget_stops_the_run(sessions: async_sessionmaker[AsyncSession]) -> None:
    llm = FakeNewsLlm(errors={"Вторая": BudgetExceeded("spent")})
    feed = rss(
        item("Первая", "https://www.kommersant.ru/1", NOW - timedelta(hours=3)),
        item("Вторая", "https://www.kommersant.ru/2", NOW - timedelta(hours=2)),
        item("Третья", "https://www.kommersant.ru/3", NOW - timedelta(hours=1)),
    )

    with pytest.raises(BudgetExceeded):
        await ingest(sessions, llm, {KOMMERSANT: feed})

    assert await stored(sessions) == ["Первая"]


async def test_broken_feeds_do_not_stop_the_others(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    broken = "https://www.interfax.ru/rss.asp"
    feeds: dict[str, bytes | int] = {
        KOMMERSANT: 503,
        broken: b"<rss><channel><item>",
        VEDOMOSTI: rss(item("Новость", "https://www.vedomosti.ru/1", NOW)),
    }

    result = await ingest(sessions, FakeNewsLlm(), feeds)

    assert result.failed_feeds == (KOMMERSANT, broken)
    assert result.added == 1


@pytest.fixture
async def index(sessions: async_sessionmaker[AsyncSession]) -> NewsIndex:
    answers = {
        "Ставка и банки": answer(
            factors=[factor("key_rate", 0.9)], industries=["finance"], regions=["Москва"]
        ),
        "Ставка вскользь": answer(factors=[factor("key_rate", 0.3)]),
        "Перевозчики Петербурга": answer(
            factors=[factor("trade_logistics", 0.6)],
            industries=["logistics"],
            regions=["Санкт-Петербург"],
        ),
        "Импорт из Китая": answer(countries=["Китай"]),
        "Давняя ставка": answer(factors=[factor("key_rate", 1.0)], industries=["finance"]),
    }
    feed = rss(
        item("Ставка вскользь", "https://www.kommersant.ru/1", NOW - timedelta(hours=1)),
        item("Ставка и банки", "https://www.kommersant.ru/2", NOW - timedelta(hours=5)),
        item("Перевозчики Петербурга", "https://www.kommersant.ru/3", NOW),
        item("Импорт из Китая", "https://www.kommersant.ru/4", NOW),
        item("Давняя ставка", "https://www.kommersant.ru/5", NOW - timedelta(days=10)),
    )
    llm = FakeNewsLlm(answers=answers)
    await ingest(sessions, llm, {KOMMERSANT: feed})
    return NewsIndex(sessions, llm, CONFIG, lambda: NOW)


async def titles(index: NewsIndex, factors: list[str], **filters: Any) -> list[str]:
    params: dict[str, Any] = {"industry": None, "region": None, "country": None, "since": SINCE}
    news = await index.search(factors, **{**params, **filters})
    return [item.title for item in news]


async def test_search_by_factor_ranks_by_strength_and_matches(index: NewsIndex) -> None:
    assert await titles(index, ["key_rate"], industry="finance") == [
        "Давняя ставка",
        "Ставка и банки",
        "Ставка вскользь",
    ]


async def test_search_by_industry_alone(index: NewsIndex) -> None:
    assert await titles(index, [], industry="logistics") == ["Перевозчики Петербурга"]


async def test_search_by_region_and_country_ignores_case(index: NewsIndex) -> None:
    assert await titles(index, [], region="САНКТ-ПЕТЕРБУРГ") == ["Перевозчики Петербурга"]
    assert await titles(index, [], country="КИТАЙ") == ["Импорт из Китая"]


async def test_search_skips_news_before_since(index: NewsIndex) -> None:
    since = (NOW - timedelta(days=3)).date()

    assert "Давняя ставка" not in await titles(index, ["key_rate"], since=since)


async def test_search_respects_limit_and_returns_contract_items(index: NewsIndex) -> None:
    [news] = await index.search(["key_rate"], "finance", None, None, SINCE, limit=1)

    assert news.title == "Давняя ставка"
    assert news.url == "https://www.kommersant.ru/5"
    assert news.factors[0].strength == 1.0
    assert "industry:finance" in news.entities


async def test_search_without_matches_is_empty(index: NewsIndex) -> None:
    assert await titles(index, ["labor_market"], industry="pharma") == []


async def test_adding_known_news_again_reports_nothing_added(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    entry = FeedEntry("Ставка", "", "https://www.kommersant.ru/1", NOW, "kommersant.ru")
    news = to_news_item(entry, SCHEMA.model_validate(KEY_RATE_ANSWER))

    async with sessions() as session, session.begin():
        first = await add_news(session, news, unit(0))
        second = await add_news(session, news, unit(1))

    assert (first, second) == (True, False)


async def test_embedding_column_has_model_dimension(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    query = text(
        "SELECT atttypmod FROM pg_attribute "
        "WHERE attrelid = 'news'::regclass AND attname = 'embedding'"
    )
    async with sessions() as session:
        assert await session.scalar(query) == EMBEDDING_DIMENSION
