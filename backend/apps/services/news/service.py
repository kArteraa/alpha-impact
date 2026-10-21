from collections.abc import Callable, Collection
from datetime import UTC, date, datetime, time

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.news.annotation import (
    COUNTRY,
    INDUSTRY,
    REGION,
    annotate,
    annotation_schema,
    entity,
    news_id,
    to_news_item,
)
from apps.services.news.config import NewsConfig
from apps.services.news.repository import matching
from shared.contracts.ports import LLMGateway
from shared.contracts.schemas import Factor, NewsItem, PageContext
from shared.db.models import NewsRow

MANUAL_SOURCE = "manual"


def query_entities(industry: str | None, region: str | None, country: str | None) -> list[str]:
    wanted = ((INDUSTRY, industry), (REGION, region), (COUNTRY, country))
    return [entity(kind, value) for kind, value in wanted if value]


def score(row: NewsRow, factors: Collection[str], entities: Collection[str]) -> float:
    strength = sum(float(factor["strength"]) for factor in row.factors if factor["name"] in factors)
    return strength + sum(1 for key in row.entities if key in entities)


def as_news_item(row: NewsRow) -> NewsItem:
    return NewsItem.model_validate(row, from_attributes=True)


class NewsIndex:
    def __init__(
        self,
        sessions: async_sessionmaker[AsyncSession],
        llm: LLMGateway,
        config: NewsConfig,
        now: Callable[[], datetime],
    ) -> None:
        self._sessions = sessions
        self._llm = llm
        self._config = config
        self._schema = annotation_schema(config)
        self._now = now

    async def search(
        self,
        factors: list[str],
        industry: str | None,
        region: str | None,
        country: str | None,
        since: date,
        limit: int = 10,
    ) -> list[NewsItem]:
        entities = query_entities(industry, region, country)
        if not factors and not entities:
            return []
        start = datetime.combine(since, time.min, tzinfo=UTC)
        async with self._sessions() as session:
            rows = await matching(session, factors, entities, start)
        wanted, keys = set(factors), set(entities)
        ranked = sorted(
            rows, key=lambda row: (score(row, wanted, keys), row.published_at), reverse=True
        )
        return [as_news_item(row) for row in ranked[:limit]]

    async def annotate(self, title: str, text: str, url: str) -> NewsItem:
        annotation, _, _ = await annotate(self._llm, self._config, self._schema, title, text)
        return to_news_item(
            news_id(title), title, text, url, self._now(), MANUAL_SOURCE, annotation
        )


class PageClassifier:
    async def classify(self, page: PageContext) -> tuple[str, list[str], list[Factor]]:
        raise NotImplementedError("AH-30")
