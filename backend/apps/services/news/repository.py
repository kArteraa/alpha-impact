from collections.abc import Sequence
from datetime import datetime, timedelta

from sqlalchemy import func, or_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from shared.contracts.schemas import Factor, NewsItem
from shared.db.models import NewsRow


async def known(
    session: AsyncSession, ids: Sequence[str], urls: Sequence[str]
) -> tuple[set[str], set[str]]:
    query = select(NewsRow.id, NewsRow.url).where(or_(NewsRow.id.in_(ids), NewsRow.url.in_(urls)))
    rows = (await session.execute(query)).all()
    return {row.id for row in rows}, {row.url for row in rows}


async def find_news(session: AsyncSession, news_id: str, url: str) -> NewsRow | None:
    query = (
        select(NewsRow)
        .options(defer(NewsRow.embedding))
        .where(or_(NewsRow.id == news_id, NewsRow.url == url))
        .order_by(NewsRow.id != news_id)
        .limit(1)
    )
    return (await session.scalars(query)).first()


async def neighbours(
    session: AsyncSession, vector: list[float], moment: datetime, window: timedelta, limit: int
) -> list[tuple[NewsRow, float]]:
    distance = NewsRow.embedding.cosine_distance(vector)
    query = (
        select(NewsRow, distance)
        .options(defer(NewsRow.embedding))
        .where(NewsRow.published_at.between(moment - window, moment + window))
        .order_by(distance)
        .limit(limit)
    )
    rows = (await session.execute(query)).all()
    return [(row, 1 - float(value)) for row, value in rows]


async def add_news(session: AsyncSession, item: NewsItem, vector: list[float]) -> bool:
    values = {
        **item.model_dump(),
        "factor_names": [factor.name for factor in item.factors],
        "embedding": vector,
    }
    statement = insert(NewsRow).values(**values).on_conflict_do_nothing().returning(NewsRow.id)
    return (await session.execute(statement)).first() is not None


async def matching(
    session: AsyncSession, factors: list[str], entities: list[str], since: datetime, limit: int
) -> Sequence[NewsRow]:
    query = select(NewsRow).options(defer(NewsRow.embedding)).where(NewsRow.published_at >= since)
    if factors or entities:
        overlaps = or_(NewsRow.factor_names.overlap(factors), NewsRow.entities.overlap(entities))
        query = query.where(overlaps)
    else:
        query = query.order_by(NewsRow.published_at.desc(), NewsRow.id).limit(limit)
    return (await session.scalars(query)).all()


async def news_count(session: AsyncSession) -> int:
    return (await session.execute(select(func.count()).select_from(NewsRow))).scalar_one()


async def stored_news(session: AsyncSession) -> list[tuple[str, str, str, str]]:
    query = select(NewsRow.id, NewsRow.url, NewsRow.title, NewsRow.text).order_by(
        NewsRow.published_at
    )
    return [(row.id, row.url, row.title, row.text) for row in (await session.execute(query)).all()]


async def update_annotation(
    session: AsyncSession, news_id: str, entities: list[str], factors: list[Factor]
) -> None:
    statement = (
        update(NewsRow)
        .where(NewsRow.id == news_id)
        .values(
            entities=entities,
            factors=[factor.model_dump() for factor in factors],
            factor_names=[factor.name for factor in factors],
        )
    )
    await session.execute(statement)
