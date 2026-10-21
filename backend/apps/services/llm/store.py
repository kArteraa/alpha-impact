from datetime import date, timedelta
from decimal import Decimal
from typing import Protocol

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.db.models import LlmCacheRow, LlmUsageRow

BUDGET_LOCK = 16_016


class UsageStore(Protocol):
    async def cached(self, key: str) -> str | None: ...
    async def remember(self, key: str, content: str) -> None: ...
    async def reserve(
        self, day: date, task: str, model: str, amount_rub: float, spendable_rub: float
    ) -> int | None: ...
    async def settle(
        self, reservation: int, tokens_in: int, tokens_out: int, cost_rub: float
    ) -> None: ...
    async def spent_rub(self, day: date) -> float: ...


class SqlUsageStore:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], cache_ttl_seconds: int) -> None:
        self._sessions = sessions
        self._cache_ttl = timedelta(seconds=cache_ttl_seconds)

    async def cached(self, key: str) -> str | None:
        fresh = LlmCacheRow.created_at > func.now() - self._cache_ttl
        statement = select(LlmCacheRow.content).where(LlmCacheRow.key == key, fresh)
        async with self._sessions() as session:
            return await session.scalar(statement)

    async def remember(self, key: str, content: str) -> None:
        expired = LlmCacheRow.created_at <= func.now() - self._cache_ttl
        statement = insert(LlmCacheRow).values(key=key, content=content)
        async with self._sessions() as session, session.begin():
            await session.execute(delete(LlmCacheRow).where(expired))
            await session.execute(statement.on_conflict_do_nothing(index_elements=["key"]))

    async def reserve(
        self, day: date, task: str, model: str, amount_rub: float, spendable_rub: float
    ) -> int | None:
        async with self._sessions() as session, session.begin():
            await session.execute(select(func.pg_advisory_xact_lock(BUDGET_LOCK)))
            if await self._spent(session, day) >= spendable_rub:
                return None
            row = LlmUsageRow(
                day=day,
                task=task,
                model=model,
                tokens_in=0,
                tokens_out=0,
                cost_rub=Decimal(str(amount_rub)),
            )
            session.add(row)
            await session.flush()
            return row.id

    async def settle(
        self, reservation: int, tokens_in: int, tokens_out: int, cost_rub: float
    ) -> None:
        target = LlmUsageRow.id == reservation
        async with self._sessions() as session, session.begin():
            if tokens_in == 0 and tokens_out == 0 and cost_rub == 0:
                await session.execute(delete(LlmUsageRow).where(target))
                return
            values = {
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "cost_rub": Decimal(str(cost_rub)),
            }
            await session.execute(update(LlmUsageRow).where(target).values(values))

    async def spent_rub(self, day: date) -> float:
        async with self._sessions() as session:
            return await self._spent(session, day)

    @staticmethod
    async def _spent(session: AsyncSession, day: date) -> float:
        total = func.coalesce(func.sum(LlmUsageRow.cost_rub), 0)
        spent = await session.scalar(select(total).where(LlmUsageRow.day == day))
        return float(spent or 0)
