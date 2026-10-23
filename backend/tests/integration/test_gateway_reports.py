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
    (tmp_path / "df_Uid_data_hack.csv").write_text("UID\n", encoding="utf-8")
    application = create_app()
    application.state.container.register(ReportFiles, lambda _: ReportFiles(tmp_path))
    yield application
    await application.state.container.resolve(AsyncEngine).dispose()


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def test_report_requires_session(client: httpx.AsyncClient) -> None:
    response = await client.get(f"/reports/{quote(REPORT)}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_report_opens_inline_as_pdf(client: httpx.AsyncClient) -> None:
    await client.post("/auth/mock", json={"user_id": USER})
    response = await client.get(f"/reports/{quote(REPORT)}")
    assert response.status_code == status.HTTP_200_OK
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" not in response.headers.get("content-disposition", "")
    assert response.content == CONTENT


@pytest.mark.parametrize("name", ["missing.pdf", "df_Uid_data_hack.csv"])
async def test_unknown_report_is_not_found(client: httpx.AsyncClient, name: str) -> None:
    await client.post("/auth/mock", json={"user_id": USER})
    response = await client.get(f"/reports/{name}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
