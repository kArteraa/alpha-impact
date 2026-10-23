from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.gateway.tokens import SqlExtensionTokens
from shared.db.models import UserRow
from shared.di.container import Container
from shared.di.dependency import get_container

SESSION_COOKIE = "alfa_session"

ContainerDep = Annotated[Container, Depends(get_container)]
SessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]
BearerToken = Annotated[HTTPAuthorizationCredentials | None, Depends(HTTPBearer(auto_error=False))]


async def current_user(container: ContainerDep, session_id: SessionCookie = None) -> str:
    if session_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no session")
    sessions = container.resolve(async_sessionmaker)
    async with sessions() as session:
        user = await session.get(UserRow, session_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown session")
    return user.id


async def interpret_user(
    container: ContainerDep, bearer: BearerToken, session_id: SessionCookie = None
) -> str:
    if bearer is None:
        return await current_user(container, session_id)
    tokens = container.resolve(SqlExtensionTokens)
    user_id = await tokens.user(bearer.credentials)
    if user_id is None:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


CurrentUser = Annotated[str, Depends(current_user)]
InterpretUser = Annotated[str, Depends(interpret_user)]
