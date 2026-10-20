from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from shared.db.models import UserClientRow, UserRow

USER = "user_cfo_wholesale"


@pytest.fixture
async def app(sessions: async_sessionmaker[AsyncSession]) -> AsyncIterator[FastAPI]:
    from main import create_app

    async with sessions() as session, session.begin():
        session.add(UserRow(id=USER, name="Финансовый директор"))
        await session.flush()
        session.add_all(
            [
                UserClientRow(user_id=USER, client_id="U_1"),
                UserClientRow(user_id=USER, client_id="U_2"),
            ]
        )
    application = create_app()
    yield application
    await application.state.container.resolve(AsyncEngine).dispose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_mock_login_sets_session_cookie(client: httpx.AsyncClient) -> None:
    response = await client.post("/auth/mock", json={"user_id": USER})
    assert response.status_code == 200
    assert response.json() == {"user_id": USER}
    assert client.cookies.get("alfa_session") == USER


async def test_unknown_user_cannot_log_in(client: httpx.AsyncClient) -> None:
    response = await client.post("/auth/mock", json={"user_id": "nobody"})
    assert response.status_code == 404


async def test_clients_requires_session(client: httpx.AsyncClient) -> None:
    assert (await client.get("/clients")).status_code == 401


async def test_clients_lists_bound_companies(client: httpx.AsyncClient) -> None:
    await client.post("/auth/mock", json={"user_id": USER})
    response = await client.get("/clients")
    assert response.status_code == 200
    assert sorted(response.json()) == ["U_1", "U_2"]


@pytest.mark.parametrize(
    ("method", "path", "task"),
    [
        ("POST", "/interpret", "AH-19"),
        ("GET", "/profile/U_1", "AH-19"),
        ("PATCH", "/profile/U_1/features/industry", "AH-19"),
        ("POST", "/feedback", "AH-23"),
        ("GET", "/trace/t1", "AH-23"),
        ("GET", "/metrics", "AH-23"),
        ("POST", "/auth/extension-token", "AH-37"),
    ],
)
async def test_unimplemented_routes_name_their_task(
    client: httpx.AsyncClient, method: str, path: str, task: str
) -> None:
    response = await client.request(method, path)
    assert response.status_code == 501
    assert task in response.json()["detail"]
