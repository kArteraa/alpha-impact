from typing import Annotated

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import async_sessionmaker

from shared.db.models import UserRow
from shared.di.container import Container
from shared.di.dependency import get_container

SESSION_COOKIE = "alfa_session"

ContainerDep = Annotated[Container, Depends(get_container)]
SessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]


async def current_user(container: ContainerDep, session_id: SessionCookie = None) -> str:
    if session_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no session")
    sessions = container.resolve(async_sessionmaker)
    async with sessions() as session:
        user = await session.get(UserRow, session_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown session")
    return user.id


CurrentUser = Annotated[str, Depends(current_user)]
