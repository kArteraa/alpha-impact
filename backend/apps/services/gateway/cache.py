import hashlib
import json
from datetime import timedelta
from typing import Protocol

from pydantic import BaseModel
from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.contracts.schemas import ActionContext, InterpretRequest, InterpretResponse, PageContext
from shared.db.models import InterpretCacheRow


def sha256(payload: object) -> str:
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def context_hash(context: BaseModel) -> str:
    return sha256(context.model_dump(mode="json"))


def normalized(context: ActionContext) -> ActionContext:
    if isinstance(context, PageContext):
        return context.model_copy(update={"text": context.text.strip()})
    return context


def cache_key(request: InterpretRequest, profile_version: int, house_view_version: str) -> str:
    context = normalized(request.action_context)
    return sha256(
        [
            request.user_id,
            request.client_id,
            request.role,
            context.type,
            context_hash(context),
            profile_version,
            house_view_version,
        ]
    )


class InterpretCache(Protocol):
    async def get(self, key: str) -> InterpretResponse | None: ...
    async def put(self, key: str, response: InterpretResponse) -> None: ...


class SqlInterpretCache:
    def __init__(self, sessions: async_sessionmaker[AsyncSession], ttl_seconds: int) -> None:
        self._sessions = sessions
        self._ttl = timedelta(seconds=ttl_seconds)

    async def get(self, key: str) -> InterpretResponse | None:
        fresh = InterpretCacheRow.created_at > func.now() - self._ttl
        statement = select(InterpretCacheRow.response).where(InterpretCacheRow.key == key, fresh)
        async with self._sessions() as session:
            payload = await session.scalar(statement)
        return None if payload is None else InterpretResponse.model_validate(payload)

    async def put(self, key: str, response: InterpretResponse) -> None:
        expired = InterpretCacheRow.created_at <= func.now() - self._ttl
        statement = insert(InterpretCacheRow).values(
            key=key, response=response.model_dump(mode="json")
        )
        async with self._sessions() as session, session.begin():
            await session.execute(delete(InterpretCacheRow).where(expired))
            await session.execute(statement.on_conflict_do_nothing(index_elements=["key"]))
