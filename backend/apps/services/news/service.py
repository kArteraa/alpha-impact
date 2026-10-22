from collections.abc import Callable, Collection
from datetime import UTC, date, datetime, time

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.news.annotation import annotation_schema, news_id
from apps.services.news.config import NewsConfig
from apps.services.news.feed import FeedEntry
from apps.services.news.ingest import body, index_entry
from apps.services.news.repository import MANUAL_SOURCE, find_news, matching
from shared.config.news_entities import COUNTRY, INDUSTRY, REGION, entity
from shared.contracts.errors import DomainError
from shared.contracts.ports import LLMGateway
from shared.contracts.schemas import Factor, NewsItem, PageContext
from shared.db.models import NewsRow


def manual_id(title: str, text: str) -> str:
    return news_id(body(title, text))


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
        text = text[: self._config.max_text_chars]
        key = manual_id(title, text)
        entry = FeedEntry(title, text, url or f"{MANUAL_SOURCE}:{key}", self._now(), MANUAL_SOURCE)
        stored = await self._stored(key, entry.url)
        if stored is None:
            indexed = await index_entry(
                self._sessions, self._llm, self._config, self._schema, entry, key
            )
            if indexed.added and indexed.item is not None:
                return indexed.item
            stored = indexed.repeat or await self._stored(key, entry.url)
        if stored is None:
            raise DomainError(f"Pasted news {key} was neither stored nor found")
        return NewsItem.model_validate(stored, from_attributes=True)

    async def _stored(self, key: str, url: str) -> NewsRow | None:
        async with self._sessions() as session:
            return await find_news(session, key, url)


class PageClassifier:
    async def classify(self, page: PageContext) -> tuple[str, list[str], list[Factor]]:
        raise NotImplementedError("AH-30")
