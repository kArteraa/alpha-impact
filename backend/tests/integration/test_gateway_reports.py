from collections.abc import AsyncIterator
from pathlib import Path
from urllib.parse import quote

import httpx
import pytest
from fastapi import FastAPI, status
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from apps.services.gateway.reports import ReportFiles
from shared.db.models import UserRow

USER = "user_cfo_wholesale"
REPORT = "Бонд_Бриф_14092026.pdf"
CONTENT = b"%PDF-1.4 bank report"


@pytest.fixture
async def app(sessions: async_sessionmaker[AsyncSession], tmp_path: Path) -> AsyncIterator[FastAPI]:
    from main import create_app

    async with sessions() as session, session.begin():
        session.add(UserRow(id=USER, name="Финансовый директор"))
    (tmp_path / REPORT).write_bytes(CONTENT)
    application = create_app()
    application.state.container.register(ReportFiles, lambda _: ReportFiles(tmp_path))
    yield application
    await application.state.container.resolve(AsyncEngine).dispose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
async def logged_in(client: httpx.AsyncClient) -> httpx.AsyncClient:
    await client.post("/auth/mock", json={"user_id": USER})
    return client


async def test_report_requires_session(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/reports/{quote(REPORT)}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_report_opens_inline_as_pdf(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.get(f"/reports/{quote(REPORT)}")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" not in response.headers.get("content-disposition", "")
    assert response.content == CONTENT


async def test_unknown_report_is_not_found(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.get("/reports/missing.pdf")
    assert response.status_code == status.HTTP_404_NOT_FOUND
