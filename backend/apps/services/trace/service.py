from datetime import UTC, date, datetime, time

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.trace.metrics import trace_metrics
from shared.contracts.errors import AccessDenied, NotFound
from shared.contracts.schemas import Trace
from shared.db.models import FeedbackRow, TraceRow


class TraceRepository:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def save(self, trace: Trace) -> None:
        async with self._sessions() as session, session.begin():
            session.add(
                TraceRow(
                    id=trace.id,
                    user_id=trace.request.user_id,
                    client_id=trace.request.client_id,
                    action_type=trace.request.action_context.type,
                    payload=trace.model_dump(mode="json"),
                    created_at=trace.created_at,
                )
            )

    async def get(self, trace_id: str) -> Trace | None:
        async with self._sessions() as session:
            payload = await session.scalar(select(TraceRow.payload).where(TraceRow.id == trace_id))
        return None if payload is None else Trace.model_validate(payload)

    async def metrics(self, since: date) -> dict[str, float]:
        start = datetime.combine(since, time.min, tzinfo=UTC)
        async with self._sessions() as session:
            payloads = await session.scalars(
                select(TraceRow.payload).where(TraceRow.created_at >= start)
            )
            traces = [Trace.model_validate(payload) for payload in payloads]
        return trace_metrics(traces)

    async def feedback(self, user_id: str, card_id: str, useful: bool, comment: str | None) -> None:
        card_trace = select(TraceRow.id, TraceRow.user_id).where(
            TraceRow.payload.contains({"result": {"cards": [{"id": card_id}]}})
        )
        async with self._sessions() as session, session.begin():
            owner = (await session.execute(card_trace)).first()
            if owner is None:
                raise NotFound(f"Unknown card {card_id}")
            if owner.user_id != user_id:
                raise AccessDenied(f"Card {card_id} belongs to another user")
            values = {"trace_id": owner.id, "useful": useful, "comment": comment}
            await session.execute(
                insert(FeedbackRow)
                .values(card_id=card_id, **values)
                .on_conflict_do_update(
                    index_elements=[FeedbackRow.card_id],
                    set_={**values, "created_at": func.now()},
                )
            )

    async def find_by_card(self, *, user_id: str, client_id: str, card_id: str) -> Trace:
        raise NotImplementedError("AH-26")
