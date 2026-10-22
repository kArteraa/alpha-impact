from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.news.annotation import news_id
from apps.services.news.config import load_config
from apps.services.news.service import MANUAL_SOURCE, NewsIndex
from shared.contracts.schemas import NewsItem
from shared.db.models import NewsRow
from tests.integration.test_prefilter_services import persist
from tests.news_data import KEY_RATE_ANSWER, NOW, FakeNewsLlm, near, unit

CONFIG = load_config()
TITLE = "Ставка снижена до 16%"
TEXT = "ЦБ снизил ключевую ставку до 16% годовых"
URL = "https://a.example/1"


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

    assert item.id == news_id(TITLE)
    assert (item.source, item.published_at, item.url) == (MANUAL_SOURCE, NOW, URL)
    assert [factor.name for factor in item.factors] == ["key_rate"]
    assert "industry:finance" in item.entities
    assert llm.tasks == [CONFIG.llm_task]
    [row] = await rows(sessions)
    assert (row.id, row.source, row.url, row.factor_names) == (
        item.id,
        MANUAL_SOURCE,
        URL,
        ["key_rate"],
    )


async def test_annotation_prompt_is_cut_to_limit(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm()

    await index(sessions, llm).annotate("Заголовок", "я" * (CONFIG.max_text_chars * 2), URL)

    assert llm.completions[0].count("я") == CONFIG.max_text_chars


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


async def test_same_news_in_other_words_comes_from_index(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    llm = FakeNewsLlm(
        vectors={"ЦБ снизил": unit(0), "Банк России понизил": near(0, 1)},
        answers={"Ставка": KEY_RATE_ANSWER},
    )
    first = await index(sessions, llm).annotate(TITLE, TEXT, URL)

    again = await index(sessions, llm).annotate(
        "Ключевая ставка — 16%", "Банк России понизил ставку до 16% годовых", ""
    )

    assert again == first
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

    assert other.id == news_id("Ключевая ставка — 17%")
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
