from datetime import timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.news import service
from apps.services.news.config import load_config
from apps.services.news.service import MANUAL_SOURCE, NewsIndex, manual_id
from shared.contracts.schemas import NewsItem
from shared.db.models import NewsRow
from tests.integration.test_news_index import ingest
from tests.integration.test_prefilter_services import persist
from tests.news_data import KEY_RATE_ANSWER, NOW, FakeNewsLlm, item, near, rss, unit

CONFIG = load_config()
TITLE = "Ставка снижена до 16%"
TEXT = "ЦБ снизил ключевую ставку до 16% годовых"
URL = "https://a.example/1"
OTHER_TITLE = "Ключевая ставка — 16%"
OTHER_TEXT = "Банк России понизил ставку до 16% годовых"


def index(sessions: async_sessionmaker[AsyncSession], llm: FakeNewsLlm) -> NewsIndex:
    return NewsIndex(sessions, llm, CONFIG, lambda: NOW)


async def rows(sessions: async_sessionmaker[AsyncSession]) -> list[NewsRow]:
    async with sessions() as session:
        return list((await session.scalars(select(NewsRow).order_by(NewsRow.title))).all())


async def test_pasted_news_is_annotated_and_stored_as_manual(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm(answers={"Ставка": KEY_RATE_ANSWER})

    item = await index(sessions, llm).annotate(TITLE, TEXT, URL)

    assert item.id == manual_id(TITLE, TEXT)
    assert (item.source, item.published_at, item.url) == (
        MANUAL_SOURCE,
        NOW,
        f"{MANUAL_SOURCE}:{item.id}",
    )
    assert [factor.name for factor in item.factors] == ["key_rate"]
    assert "industry:finance" in item.entities
    assert llm.tasks == [CONFIG.llm_task]
    [row] = await rows(sessions)
    assert (row.id, row.source, row.url, row.factor_names) == (
        item.id,
        MANUAL_SOURCE,
        item.url,
        ["key_rate"],
    )


async def test_pasted_text_is_cut_to_limit_everywhere(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm()

    item = await index(sessions, llm).annotate("Заголовок", "я" * (CONFIG.max_text_chars * 2), URL)

    assert llm.completions[0].count("я") == CONFIG.max_text_chars
    assert llm.embedded[0].count("я") == CONFIG.max_text_chars
    assert len(item.text) == CONFIG.max_text_chars
    [row] = await rows(sessions)
    assert row.text == item.text


async def test_identical_paste_comes_from_index_without_model(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm(answers={"Ставка": KEY_RATE_ANSWER})
    first = await index(sessions, llm).annotate(TITLE, TEXT, "")

    again = await index(sessions, llm).annotate(TITLE, TEXT, "")

    assert again == first
    assert llm.tasks == [CONFIG.llm_task]
    assert len(llm.embedded) == 1
    assert len(await rows(sessions)) == 1


async def test_same_news_in_other_words_reuses_annotation_with_own_text(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm(
        vectors={"ЦБ снизил": unit(0), "Банк России понизил": near(0, 1)},
        answers={"Ставка": KEY_RATE_ANSWER},
    )
    first = await index(sessions, llm).annotate(TITLE, TEXT, URL)

    again = await index(sessions, llm).annotate(OTHER_TITLE, OTHER_TEXT, "")

    assert again.id == manual_id(OTHER_TITLE, OTHER_TEXT)
    assert (again.title, again.text, again.source) == (OTHER_TITLE, OTHER_TEXT, MANUAL_SOURCE)
    assert (again.factors, again.entities) == (first.factors, first.entities)
    assert llm.tasks == [CONFIG.llm_task]
    assert len(await rows(sessions)) == 2


async def test_paste_close_to_feed_news_returns_feed_news(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm(vectors={"ЦБ снизил": unit(0), "Банк России понизил": near(0, 1)})
    feed = rss(item(TITLE, "https://www.kommersant.ru/doc/9", NOW, TEXT))
    await ingest(sessions, llm, {"https://www.kommersant.ru/rss/x.xml": feed})
    [feed_row] = await rows(sessions)

    found = await index(sessions, llm).annotate(OTHER_TITLE, OTHER_TEXT, "")

    assert (found.id, found.text, found.source) == (feed_row.id, TEXT, feed_row.source)
    assert llm.tasks == [CONFIG.llm_task]
    assert len(await rows(sessions)) == 1


async def test_close_text_with_other_numbers_is_new_news(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm(vectors={"ЦБ снизил": unit(0), "Банк России понизил": near(0, 1)})
    await index(sessions, llm).annotate(TITLE, TEXT, URL)

    other = await index(sessions, llm).annotate(
        "Ключевая ставка — 17%", "Банк России понизил ставку до 17% годовых", ""
    )

    assert other.id == manual_id(
        "Ключевая ставка — 17%", "Банк России понизил ставку до 17% годовых"
    )
    assert len(llm.tasks) == 2
    assert len(await rows(sessions)) == 2


async def test_indexed_url_comes_from_index_without_model(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm()
    feed_item = NewsItem(
        id="feed-news",
        title="Из ленты",
        text=TEXT,
        url=URL,
        published_at=NOW,
        source="kommersant.ru",
        entities=["industry:finance"],
        factors=[],
    )
    await persist(sessions, feed_item)

    found = await index(sessions, llm).annotate("Другой заголовок", "Другой текст", URL)

    assert found == feed_item
    assert llm.tasks == []
    assert llm.embedded == []


async def test_pastes_without_url_are_stored_under_manual_addresses(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm()
    first = await index(sessions, llm).annotate(TITLE, TEXT, "")

    second = await index(sessions, llm).annotate("Склады дорожают", "Аренда выросла на 12%", "")

    assert first.url == f"{MANUAL_SOURCE}:{first.id}"
    assert second.url == f"{MANUAL_SOURCE}:{second.id}"
    assert [row.url for row in await rows(sessions)] == [second.url, first.url]


async def test_same_headline_with_other_text_is_new_news(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm()
    first = await index(sessions, llm).annotate("Ключевая ставка", "ЦБ снизил ставку до 16%", "")

    other = await index(sessions, llm).annotate("Ключевая ставка", "ЦБ повысил ставку до 18%", "")

    assert other.id != first.id
    assert other.text == "ЦБ повысил ставку до 18%"
    assert len(await rows(sessions)) == 2


async def test_same_url_with_other_text_is_new_news(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm()
    first = await index(sessions, llm).annotate(TITLE, TEXT, URL)

    other = await index(sessions, llm).annotate("Склады дорожают", "Аренда выросла на 12%", URL)

    assert other.id != first.id
    assert other.text == "Аренда выросла на 12%"
    assert len(await rows(sessions)) == 2


async def test_pasted_news_is_not_served_by_search(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm(answers={"Ставка": KEY_RATE_ANSWER})
    news = index(sessions, llm)
    await news.annotate(TITLE, TEXT, URL)

    since = (NOW - timedelta(days=1)).date()
    assert await news.search([], None, None, None, since) == []
    assert await news.search(["key_rate"], "finance", None, None, since) == []


async def test_feed_copy_of_pasted_news_is_still_ingested(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm(vectors={"ЦБ снизил": unit(0)})
    await index(sessions, llm).annotate(TITLE, TEXT, "")
    feed = rss(item(TITLE, "https://www.kommersant.ru/doc/9", NOW, TEXT))

    result = await ingest(sessions, llm, {"https://www.kommersant.ru/rss/x.xml": feed})

    assert (result.added, result.duplicates) == (1, 0)


async def test_feed_news_with_headline_of_one_line_paste_is_still_ingested(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm()
    news = index(sessions, llm)
    await news.annotate(TITLE, "", "")
    feed = rss(item(TITLE, "https://www.kommersant.ru/doc/9", NOW, TEXT))

    result = await ingest(sessions, llm, {"https://www.kommersant.ru/rss/x.xml": feed})

    assert result.added == 1
    since = (NOW - timedelta(days=1)).date()
    assert [found.title for found in await news.search([], None, None, None, since)] == [TITLE]


async def test_feed_news_at_pasted_url_is_still_ingested(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm()
    await index(sessions, llm).annotate(TITLE, TEXT, URL)
    feed = rss(item("Склады дорожают", URL, NOW, "Аренда выросла на 12%"))

    result = await ingest(sessions, llm, {"https://a.example/rss.xml": feed})

    assert result.added == 1


async def test_lost_insert_returns_stored_news(
    sessions: async_sessionmaker[AsyncSession], monkeypatch: pytest.MonkeyPatch
) -> None:
    stored = NewsItem(
        id=manual_id(TITLE, TEXT),
        title=TITLE,
        text=TEXT,
        url=URL,
        published_at=NOW - timedelta(days=30),
        source=MANUAL_SOURCE,
        entities=[],
        factors=[],
    )
    await persist(sessions, stored)
    real = service.find_news
    calls: list[str] = []

    async def first_misses(session: AsyncSession, news_id: str, url: str) -> NewsRow | None:
        calls.append(news_id)
        return None if len(calls) == 1 else await real(session, news_id, url)

    monkeypatch.setattr(service, "find_news", first_misses)

    found = await index(sessions, FakeNewsLlm()).annotate(TITLE, TEXT, URL)

    assert found == stored
    assert len(await rows(sessions)) == 1
