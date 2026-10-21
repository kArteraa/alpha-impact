from datetime import date

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services import news
from apps.services.news.annotation import news_id
from apps.services.news.config import load_config
from apps.services.news.service import MANUAL_SOURCE, NewsIndex
from shared.contracts.ports import LLMGateway, NewsService, PageContextService
from shared.contracts.schemas import PageContext
from shared.di.container import Container
from tests.news_data import KEY_RATE_ANSWER, NOW, FakeNewsLlm

CONFIG = load_config()


def container() -> Container:
    result = Container()
    result.register(async_sessionmaker, lambda _: async_sessionmaker())
    result.register(LLMGateway, lambda _: FakeNewsLlm())
    news.register(result)
    return result


def index(llm: FakeNewsLlm) -> NewsIndex:
    return NewsIndex(async_sessionmaker(), llm, CONFIG, lambda: NOW)


def test_news_index_implements_port() -> None:
    assert isinstance(container().resolve(NewsService), NewsService)


def test_page_classifier_implements_port() -> None:
    assert isinstance(container().resolve(PageContextService), PageContextService)


async def test_annotate_marks_up_pasted_news_without_saving_it() -> None:
    llm = FakeNewsLlm(answers={"Ставка": KEY_RATE_ANSWER})

    item = await index(llm).annotate("Ставка снижена", "ЦБ снизил ставку", "https://a.example/1")

    assert item.id == news_id("Ставка снижена")
    assert (item.source, item.published_at, item.url) == (MANUAL_SOURCE, NOW, "https://a.example/1")
    assert [factor.name for factor in item.factors] == ["key_rate"]
    assert "industry:finance" in item.entities
    assert llm.tasks == [CONFIG.llm_task]


async def test_annotate_sends_text_cut_to_limit() -> None:
    llm = FakeNewsLlm()

    await index(llm).annotate("Заголовок", "я" * (CONFIG.max_text_chars * 2), "https://a.example/1")

    assert llm.completions[0].count("я") == CONFIG.max_text_chars


async def test_search_without_criteria_is_empty() -> None:
    assert await index(FakeNewsLlm()).search([], None, None, None, date(2026, 10, 7)) == []


async def test_classify_points_to_task() -> None:
    page = PageContext(url="https://example.com", text="x")
    with pytest.raises(NotImplementedError, match="AH-30"):
        await container().resolve(PageContextService).classify(page)
