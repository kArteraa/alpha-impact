from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from shared.db.models import NewsRow


async def known(
    session: AsyncSession, ids: Sequence[str], urls: Sequence[str]
) -> tuple[set[str], set[str]]:
    query = select(NewsRow.id, NewsRow.url).where(or_(NewsRow.id.in_(ids), NewsRow.url.in_(urls)))
    rows = (await session.execute(query)).all()
    return {row.id for row in rows}, {row.url for row in rows}


async def neighbours(
    session: AsyncSession, vector: list[float], moment: datetime, window: timedelta, limit: int
) -> list[tuple[str, str, float]]:
    distance = NewsRow.embedding.cosine_distance(vector)
    query = (
        select(NewsRow.title, NewsRow.text, distance)
        .where(NewsRow.published_at.between(moment - window, moment + window))
        .order_by(distance)
        .limit(limit)
    )
    rows = (await session.execute(query)).all()
    return [(title, text, 1 - float(value)) for title, text, value in rows]


async def add_news(session: AsyncSession, values: dict[str, Any]) -> None:
    await session.execute(insert(NewsRow).values(**values).on_conflict_do_nothing())


async def matching(
    session: AsyncSession, factors: Sequence[str], entities: Sequence[str], since: datetime
) -> Sequence[NewsRow]:
    conditions = []
    if factors:
        conditions.append(NewsRow.factor_names.overlap(list(factors)))
    if entities:
        conditions.append(NewsRow.entities.overlap(list(entities)))
    query = (
        select(NewsRow)
        .options(defer(NewsRow.embedding))
        .where(NewsRow.published_at >= since, or_(*conditions))
    )
    return (await session.scalars(query)).all()


async def news_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(NewsRow)) or 0)
