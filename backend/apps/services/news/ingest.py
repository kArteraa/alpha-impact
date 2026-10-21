import xml.etree.ElementTree as ElementTree
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta

import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.news.annotation import annotate, annotation_schema, news_id, to_news_item
from apps.services.news.config import NewsConfig
from apps.services.news.dedup import is_duplicate, numbers
from apps.services.news.feed import FeedEntry, FeedTooLarge, fetch_feed
from apps.services.news.repository import add_news, known, neighbours, news_count
from shared.contracts.errors import BudgetExceeded, DomainError
from shared.contracts.ports import LLMGateway


@dataclass(frozen=True)
class IngestResult:
    added: int
    duplicates: int
    failed: tuple[str, ...]
    failed_feeds: tuple[str, ...]
    tokens_in: int
    tokens_out: int
    total: int


def body(title: str, text: str) -> str:
    return f"{title}\n{text}".strip()


async def collect(
    http: httpx.AsyncClient, urls: Sequence[str], max_bytes: int
) -> tuple[list[FeedEntry], tuple[str, ...]]:
    entries: list[FeedEntry] = []
    failed: list[str] = []
    for url in urls:
        try:
            entries.extend(await fetch_feed(http, url, max_bytes))
        except (httpx.HTTPError, ElementTree.ParseError, FeedTooLarge):
            failed.append(url)
    return entries, tuple(failed)


def fresh(entries: Sequence[FeedEntry], since: datetime) -> list[FeedEntry]:
    by_id: dict[str, FeedEntry] = {}
    urls: set[str] = set()
    for entry in sorted(entries, key=lambda entry: entry.published_at):
        key = news_id(entry.title)
        if entry.published_at >= since and key not in by_id and entry.url not in urls:
            by_id[key] = entry
            urls.add(entry.url)
    return list(by_id.values())


async def unseen(
    sessions: async_sessionmaker[AsyncSession], entries: Sequence[FeedEntry]
) -> list[FeedEntry]:
    async with sessions() as session:
        ids, urls = await known(
            session, [news_id(entry.title) for entry in entries], [entry.url for entry in entries]
        )
    return [entry for entry in entries if news_id(entry.title) not in ids and entry.url not in urls]


async def repeats_indexed(
    sessions: async_sessionmaker[AsyncSession],
    entry: FeedEntry,
    vector: list[float],
    config: NewsConfig,
) -> bool:
    window = timedelta(hours=config.dedup_window_hours)
    async with sessions() as session:
        nearby = await neighbours(
            session, vector, entry.published_at, window, config.dedup_candidates
        )
    own = numbers(body(entry.title, entry.text))
    return any(
        is_duplicate(similarity, own, numbers(body(title, text)), config.dedup_threshold)
        for title, text, similarity in nearby
    )


async def ingest_news(
    sessions: async_sessionmaker[AsyncSession],
    llm: LLMGateway,
    http: httpx.AsyncClient,
    urls: Sequence[str],
    config: NewsConfig,
    now: datetime,
) -> IngestResult:
    entries, failed_feeds = await collect(http, urls, config.max_feed_bytes)
    candidates = await unseen(sessions, fresh(entries, now - timedelta(days=config.max_age_days)))
    schema = annotation_schema(config)
    added = duplicates = tokens_in = tokens_out = 0
    failed: list[str] = []
    for entry in candidates:
        vector = await llm.embed(body(entry.title, entry.text))
        if await repeats_indexed(sessions, entry, vector, config):
            duplicates += 1
            continue
        try:
            annotation, used_in, used_out = await annotate(
                llm, config, schema, entry.title, entry.text
            )
        except BudgetExceeded:
            raise
        except DomainError:
            failed.append(entry.url)
            continue
        async with sessions() as session, session.begin():
            await add_news(session, to_news_item(entry, annotation), vector)
        added += 1
        tokens_in += used_in
        tokens_out += used_out
    async with sessions() as session:
        total = await news_count(session)
    return IngestResult(
        added, duplicates, tuple(failed), failed_feeds, tokens_in, tokens_out, total
    )
