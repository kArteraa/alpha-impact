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
    to_news_item,
)
from apps.services.news.config import NewsConfig
from apps.services.news.feed import FeedEntry
from apps.services.news.repository import matching
from shared.config.geography import country_code, region_name
from shared.contracts.ports import LLMGateway
from shared.contracts.schemas import Factor, NewsItem, PageContext

MANUAL_SOURCE = "manual"


def query_entities(industry: str | None, region: str | None, country: str | None) -> list[str]:
    subject = region_name(region) if region else None
    code = country_code(country) if country else None
    wanted = ((INDUSTRY, industry), (REGION, subject), (COUNTRY, code))
    return [entity(kind, value) for kind, value in wanted if value]


def score(item: NewsItem, factors: Collection[str], entities: Collection[str]) -> float:
    strength = sum(factor.strength for factor in item.factors if factor.name in factors)
    return strength + sum(1 for key in item.entities if key in entities)


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
        items = [NewsItem.model_validate(row, from_attributes=True) for row in rows]
        wanted, keys = set(factors), set(entities)
        ranked = sorted(
            items, key=lambda item: (score(item, wanted, keys), item.published_at), reverse=True
        )
        return ranked[:limit]

    async def annotate(self, title: str, text: str, url: str) -> NewsItem:
        annotation, _, _ = await annotate(self._llm, self._config, self._schema, title, text)
        entry = FeedEntry(title, text, url, self._now(), MANUAL_SOURCE)
        return to_news_item(entry, annotation)


class PageClassifier:
    async def classify(self, page: PageContext) -> tuple[str, list[str], list[Factor]]:
        raise NotImplementedError("AH-30")
