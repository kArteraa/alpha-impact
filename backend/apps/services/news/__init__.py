from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.news.config import load_config
from apps.services.news.service import NewsIndex, PageClassifier
from shared.contracts.ports import LLMGateway, NewsService, PageContextService
from shared.di.container import Container

__all__ = ["register"]


def utc_now() -> datetime:
    return datetime.now(UTC)


def register(container: Container) -> None:
    container.register(
        NewsService,
        lambda c: NewsIndex(
            c.resolve(async_sessionmaker), c.resolve(LLMGateway), load_config(), utc_now
        ),
    )
    container.register(PageContextService, lambda _: PageClassifier())
