from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.gateway.auth import SESSION_COOKIE, ContainerDep, CurrentUser, current_user
from apps.services.gateway.errors import DomainErrorRoute
from apps.services.gateway.service import InterpretGateway
from shared.contracts.ports import ProfileService, TraceStore
from shared.contracts.schemas import (
    ClientProfile,
    InterpretRequest,
    InterpretResponse,
    Trace,
)
from shared.db.models import UserRow

router = APIRouter(route_class=DomainErrorRoute)


class MockLogin(BaseModel):
    user_id: str


class MockSession(BaseModel):
    user_id: str


class FeatureCorrection(BaseModel):
    value: str | float | bool | list[str] | None


class CardFeedback(BaseModel):
    card_id: str
    useful: bool
    comment: str | None = None


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
async def clients(user_id: CurrentUser, container: ContainerDep) -> list[str]:
    return await container.resolve(ProfileService).list_clients(user_id)


@router.post("/interpret")
async def interpret(
    body: InterpretRequest, user_id: CurrentUser, container: ContainerDep
) -> InterpretResponse:
    return await container.resolve(InterpretGateway).interpret(user_id, body)


@router.get("/profile/{client_id}")
async def profile(client_id: str, user_id: CurrentUser, container: ContainerDep) -> ClientProfile:
    return await container.resolve(ProfileService).get_profile(user_id, client_id)


@router.patch("/profile/{client_id}/features/{name}")
async def patch_feature(
    client_id: str,
    name: str,
    body: FeatureCorrection,
    user_id: CurrentUser,
    container: ContainerDep,
) -> ClientProfile:
    return await container.resolve(ProfileService).apply_user_correction(
        user_id, client_id, name, body.value
    )


@router.post("/feedback", status_code=status.HTTP_204_NO_CONTENT)
async def feedback(body: CardFeedback, user_id: CurrentUser, container: ContainerDep) -> None:
    await container.resolve(TraceStore).feedback(user_id, body.card_id, body.useful, body.comment)


@router.get("/trace/{trace_id}")
async def trace(trace_id: str, user_id: CurrentUser, container: ContainerDep) -> Trace:
    found = await container.resolve(TraceStore).get(trace_id)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "unknown trace")
    if found.request.user_id != user_id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "trace of another user")
    return found


@router.get("/metrics", dependencies=[Depends(current_user)])
async def metrics(since: date, container: ContainerDep) -> dict[str, float]:
    return await container.resolve(TraceStore).metrics(since)


@router.post("/auth/extension-token")
async def extension_token() -> None:
    raise not_implemented("AH-37")
