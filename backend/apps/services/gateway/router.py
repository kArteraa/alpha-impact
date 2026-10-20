from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from shared.db.models import UserClientRow, UserRow
from shared.di.container import Container
from shared.di.dependency import get_container

SESSION_COOKIE = "alfa_session"

router = APIRouter()
ContainerDep = Annotated[Container, Depends(get_container)]
SessionCookie = Annotated[str | None, Cookie(alias=SESSION_COOKIE)]


class MockLogin(BaseModel):
    user_id: str


class MockSession(BaseModel):
    user_id: str


def not_implemented(task: str) -> HTTPException:
    return HTTPException(status.HTTP_501_NOT_IMPLEMENTED, f"Not implemented: {task}")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/auth/mock")
async def auth_mock(body: MockLogin, response: Response, container: ContainerDep) -> MockSession:
    sessions = container.resolve(async_sessionmaker)
    async with sessions() as session:
        user = await session.get(UserRow, body.user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown user")
    response.set_cookie(SESSION_COOKIE, user.id, httponly=True, samesite="lax")
    return MockSession(user_id=user.id)


@router.get("/clients")
async def clients(container: ContainerDep, session_id: SessionCookie = None) -> list[str]:
    if session_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "no session")
    sessions = container.resolve(async_sessionmaker)
    async with sessions() as session:
        user = await session.get(UserRow, session_id)
        if user is None:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "unknown session")
        query = select(UserClientRow.client_id).where(UserClientRow.user_id == user.id)
        return list(await session.scalars(query))


@router.post("/interpret")
async def interpret() -> None:
    raise not_implemented("AH-19")


@router.get("/profile/{client_id}")
async def profile(client_id: str) -> None:
    raise not_implemented("AH-19")


@router.patch("/profile/{client_id}/features/{name}")
async def patch_feature(client_id: str, name: str) -> None:
    raise not_implemented("AH-19")


@router.post("/feedback")
async def feedback() -> None:
    raise not_implemented("AH-23")


@router.get("/trace/{trace_id}")
async def trace(trace_id: str) -> None:
    raise not_implemented("AH-23")


@router.get("/metrics")
async def metrics() -> None:
    raise not_implemented("AH-23")


@router.post("/auth/extension-token")
async def extension_token() -> None:
    raise not_implemented("AH-37")
