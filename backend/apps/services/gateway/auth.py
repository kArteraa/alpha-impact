from typing import Annotated

from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.gateway.tokens import SqlExtensionTokens
from shared.db.models import UserRow
from shared.di.container import Container
from shared.di.dependency import get_container

SESSION_COOKIE = "alfa_session"

ContainerDep = Annotated[Container, Depends(get_container)]
SessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]
AuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]


def bearer_token(authorization: str) -> str:
    scheme, _, token = authorization.partition(" ")
    return token.strip() if scheme.lower() == "bearer" else ""


async def known_user(container: Container, user_id: str) -> bool:
    sessions = container.resolve(async_sessionmaker)
    async with sessions() as session:
        return await session.get(UserRow, user_id) is not None


async def current_user(container: ContainerDep, session_id: SessionCookie = None) -> str:
    if session_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no session")
    if not await known_user(container, session_id):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown session")
    return session_id


async def interpret_user(
    container: ContainerDep,
    authorization: AuthorizationHeader = None,
    session_id: SessionCookie = None,
) -> str:
    if authorization is None:
        return await current_user(container, session_id)
    token = bearer_token(authorization)
    user_id = await container.resolve(SqlExtensionTokens).user(token) if token else None
    if user_id is None or not await known_user(container, user_id):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user_id


CurrentUser = Annotated[str, Depends(current_user)]
InterpretUser = Annotated[str, Depends(interpret_user)]
