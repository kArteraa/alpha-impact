from datetime import date

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services import news
from apps.services.news.config import load_config
from apps.services.news.service import NewsIndex
from shared.contracts.ports import LLMGateway, NewsService, PageContextService
from shared.contracts.schemas import PageContext
from shared.di.container import Container
from tests.news_data import NOW, FakeNewsLlm

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


async def test_search_rejects_nonpositive_limit_before_database_access() -> None:
    with pytest.raises(ValueError, match="limit"):
        await index(FakeNewsLlm()).search([], None, None, None, date(2026, 10, 7), limit=0)


async def test_classify_points_to_task() -> None:
    page = PageContext(url="https://example.com", text="x")
    with pytest.raises(NotImplementedError, match="AH-30"):
        await container().resolve(PageContextService).classify(page)
