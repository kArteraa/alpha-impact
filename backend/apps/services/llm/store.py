from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.db.models import LlmCacheRow, LlmUsageRow


@dataclass(frozen=True)
class Usage:
    day: date
    task: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_rub: float


class UsageStore(Protocol):
    async def cached(self, key: str) -> str | None: ...
    async def remember(self, key: str, content: str) -> None: ...
    async def record(self, usage: Usage) -> None: ...
    async def spent_rub(self, day: date) -> float: ...


class SqlUsageStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def cached(self, key: str) -> str | None:
        async with self._sessions() as session:
            return await session.scalar(select(LlmCacheRow.content).where(LlmCacheRow.key == key))

    async def remember(self, key: str, content: str) -> None:
        statement = insert(LlmCacheRow).values(key=key, content=content)
        async with self._sessions() as session, session.begin():
            await session.execute(statement.on_conflict_do_nothing(index_elements=["key"]))

    async def record(self, usage: Usage) -> None:
        async with self._sessions() as session, session.begin():
            session.add(
                LlmUsageRow(
                    day=usage.day,
                    task=usage.task,
                    model=usage.model,
                    tokens_in=usage.tokens_in,
                    tokens_out=usage.tokens_out,
                    cost_rub=Decimal(str(usage.cost_rub)),
                )
            )

    async def spent_rub(self, day: date) -> float:
        total = func.coalesce(func.sum(LlmUsageRow.cost_rub), 0)
        async with self._sessions() as session:
            spent = await session.scalar(select(total).where(LlmUsageRow.day == day))
        return float(spent or 0)
