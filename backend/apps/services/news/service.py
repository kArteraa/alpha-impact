from collections.abc import Callable, Collection
from datetime import UTC, date, datetime, time

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.news.annotation import annotation_schema, news_id
from apps.services.news.config import NewsConfig
from apps.services.news.feed import FeedEntry
from apps.services.news.ingest import index_entry
from apps.services.news.repository import find_news, matching
from shared.config.news_entities import COUNTRY, INDUSTRY, REGION, entity
from shared.contracts.ports import LLMGateway
from shared.contracts.schemas import Factor, NewsItem, PageContext

MANUAL_SOURCE = "manual"


def query_entities(industry: str | None, region: str | None, country: str | None) -> list[str]:
    wanted = ((INDUSTRY, industry), (REGION, region), (COUNTRY, country))
    return [key for kind, value in wanted if value and (key := entity(kind, value))]


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
        if limit <= 0:
            raise ValueError("Search limit must be positive")
        entities = query_entities(industry, region, country)
        if not factors and not entities and any((industry, region, country)):
            return []
        start = datetime.combine(since, time.min, tzinfo=UTC)
        async with self._sessions() as session:
            rows = await matching(session, factors, entities, start, limit)
        items = [NewsItem.model_validate(row, from_attributes=True) for row in rows]
        wanted, keys = set(factors), set(entities)
        ranked = sorted(
            items, key=lambda item: (score(item, wanted, keys), item.published_at), reverse=True
        )
        return ranked[:limit]

    async def annotate(self, title: str, text: str, url: str) -> NewsItem:
        key = news_id(title)
        address = url or f"{MANUAL_SOURCE}:{key}"
        text = text[: self._config.max_text_chars]
        entry = FeedEntry(title, text, address, self._now(), MANUAL_SOURCE)
        async with self._sessions() as session:
            known = await find_news(session, key, entry.url)
        if known is not None:
            return NewsItem.model_validate(known, from_attributes=True)
        indexed = await index_entry(self._sessions, self._llm, self._config, self._schema, entry)
        return indexed.item


class PageClassifier:
    async def classify(self, page: PageContext) -> tuple[str, list[str], list[Factor]]:
        raise NotImplementedError("AH-30")
