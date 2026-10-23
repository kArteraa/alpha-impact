import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.db.models import ExtensionTokenRow

INTERPRET_SCOPE = "interpret:read"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class SqlExtensionTokens:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], ttl_seconds: int) -> None:
        self._sessions = sessions
        self._ttl = timedelta(seconds=ttl_seconds)

    async def issue(self, user_id: str, scope: str) -> tuple[str, datetime]:
        token = secrets.token_urlsafe(32)
        statement = (
            insert(ExtensionTokenRow)
            .values(
                token_hash=token_hash(token),
                user_id=user_id,
                scope=scope,
                expires_at=func.now() + self._ttl,
            )
            .returning(ExtensionTokenRow.expires_at)
        )
        async with self._sessions() as session, session.begin():
            await session.execute(
                delete(ExtensionTokenRow).where(ExtensionTokenRow.expires_at <= func.now())
            )
            expires_at = (await session.execute(statement)).scalar_one()
        return token, expires_at

    async def user(self, token: str, scope: str) -> str | None:
        statement = select(ExtensionTokenRow.user_id).where(
            ExtensionTokenRow.token_hash == token_hash(token),
            ExtensionTokenRow.scope == scope,
            ExtensionTokenRow.expires_at > func.now(),
        )
        async with self._sessions() as session:
            return await session.scalar(statement)
