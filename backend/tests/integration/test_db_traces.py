from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.contracts.schemas import Trace
from shared.db.models import TraceRow
from tests.integration.contracts.examples import TRACE


async def test_trace_is_written_and_read_back(sessions: async_sessionmaker[AsyncSession]) -> None:
    async with sessions() as session, session.begin():
        session.add(
            TraceRow(
                id=TRACE.id,
                user_id=TRACE.request.user_id,
                client_id=TRACE.request.client_id,
                action_type=TRACE.request.action_context.type,
                payload=TRACE.model_dump(mode="json"),
            )
        )
    async with sessions() as session:
        row = await session.scalar(select(TraceRow).where(TraceRow.id == TRACE.id))
    assert row is not None
    assert Trace.model_validate(row.payload) == TRACE
    assert row.created_at is not None
