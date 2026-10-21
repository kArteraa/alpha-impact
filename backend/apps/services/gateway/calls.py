from dataclasses import asdict, dataclass
from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.db.models import GatewayCallRow


@dataclass(frozen=True)
class CallRecord:
    user_id: str
    client_id: str
    action_type: str
    context_hash: str
    trace_id: str | None
    cached: bool
    outcome: str
    duration_ms: int


class CallJournal(Protocol):
    async def record(self, call: CallRecord) -> None: ...


class SqlCallJournal:
    def __init__(self, sessions: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = sessions

    async def record(self, call: CallRecord) -> None:
        async with self._sessions() as session, session.begin():
            session.add(GatewayCallRow(**asdict(call)))
