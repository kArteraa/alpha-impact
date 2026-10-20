import pytest

from apps.services import news
from shared.contracts.ports import NewsService, PageContextService
from shared.contracts.schemas import PageContext
from shared.di.container import Container


def container() -> Container:
    result = Container()
    news.register(result)
    return result


def test_news_index_implements_port() -> None:
    assert isinstance(container().resolve(NewsService), NewsService)


def test_page_classifier_implements_port() -> None:
    assert isinstance(container().resolve(PageContextService), PageContextService)


async def test_news_methods_point_to_task() -> None:
    with pytest.raises(NotImplementedError, match="AH-13"):
        await container().resolve(NewsService).annotate("t", "x", "https://example.com")


async def test_classify_points_to_task() -> None:
    page = PageContext(url="https://example.com", text="x")
    with pytest.raises(NotImplementedError, match="AH-30"):
        await container().resolve(PageContextService).classify(page)
