import hashlib
from datetime import datetime, timedelta

import httpx
import pytest
from fastapi import status
from sqlalchemy import func, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from shared.config.settings import Settings
from shared.db.models import ExtensionTokenRow
from tests.integration.test_gateway import USER, FakeInterpreter, interpret_body
from tests.integration.test_gateway import app as app
from tests.integration.test_gateway import client as client
from tests.integration.test_gateway import house_view as house_view
from tests.integration.test_gateway import interpreter as interpreter
from tests.integration.test_gateway import logged_in as logged_in

PAGE_LINES = ["Ставка снижена до 16%", "ЦБ снизил ключевую ставку, кредиты подешевеют."]


async def issue(client: httpx.AsyncClient) -> str:
    response = await client.post("/auth/extension-token")
    assert response.status_code == status.HTTP_200_OK
    return str(response.json()["token"])


async def token_only(logged_in: httpx.AsyncClient) -> str:
    token = await issue(logged_in)
    logged_in.cookies.clear()
    return token


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def db_now(sessions: async_sessionmaker[AsyncSession]) -> datetime:
    async with sessions() as session:
        now: datetime = (await session.execute(select(func.now()))).scalar_one()
    return now


async def expire_tokens(sessions: async_sessionmaker[AsyncSession]) -> None:
    async with sessions() as session, session.begin():
        await session.execute(
            update(ExtensionTokenRow).values(expires_at=func.now() - timedelta(seconds=1))
        )


async def test_extension_token_requires_session(client: httpx.AsyncClient) -> None:
    response = await client.post("/auth/extension-token")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_extension_token_lives_configured_ttl(
    logged_in: httpx.AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    ttl = timedelta(seconds=Settings().EXTENSION_TOKEN_TTL_SECONDS)
    before = await db_now(sessions)
    response = await logged_in.post("/auth/extension-token")
    after = await db_now(sessions)
    expires_at = datetime.fromisoformat(response.json()["expires_at"])
    assert before + ttl <= expires_at <= after + ttl


async def test_interpret_accepts_extension_token_without_cookie(
    logged_in: httpx.AsyncClient, interpreter: FakeInterpreter
) -> None:
    token = await token_only(logged_in)
    response = await logged_in.post("/interpret", json=interpret_body(), headers=bearer(token))
    assert response.status_code == status.HTTP_200_OK
    assert [call.user_id for call in interpreter.calls] == [USER]


async def test_expired_extension_token_is_rejected(
    logged_in: httpx.AsyncClient,
    sessions: async_sessionmaker[AsyncSession],
    interpreter: FakeInterpreter,
) -> None:
    token = await token_only(logged_in)
    await expire_tokens(sessions)
    response = await logged_in.post("/interpret", json=interpret_body(), headers=bearer(token))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"
    assert interpreter.calls == []


@pytest.mark.parametrize("authorization", ["Bearer not-a-token", "Bearer ", "Basic dXNlcg=="])
async def test_bad_authorization_is_rejected_even_with_session(
    logged_in: httpx.AsyncClient, interpreter: FakeInterpreter, authorization: str
) -> None:
    response = await logged_in.post(
        "/interpret", json=interpret_body(), headers={"Authorization": authorization}
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert interpreter.calls == []


async def test_token_of_a_user_that_no_longer_exists_is_rejected(
    logged_in: httpx.AsyncClient,
    sessions: async_sessionmaker[AsyncSession],
    interpreter: FakeInterpreter,
) -> None:
    token = await token_only(logged_in)
    async with sessions() as session, session.begin():
        await session.execute(update(ExtensionTokenRow).values(user_id="user_gone"))
    response = await logged_in.post("/interpret", json=interpret_body(), headers=bearer(token))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert response.headers["www-authenticate"] == "Bearer"
    assert interpreter.calls == []


async def test_token_of_another_scope_is_rejected(
    logged_in: httpx.AsyncClient,
    sessions: async_sessionmaker[AsyncSession],
    interpreter: FakeInterpreter,
) -> None:
    token = await token_only(logged_in)
    async with sessions() as session, session.begin():
        await session.execute(update(ExtensionTokenRow).values(scope="profile:read"))
    response = await logged_in.post("/interpret", json=interpret_body(), headers=bearer(token))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED
    assert interpreter.calls == []


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/profile/U_1"), ("GET", "/clients"), ("POST", "/auth/extension-token")],
)
async def test_extension_token_opens_only_interpret(
    logged_in: httpx.AsyncClient, method: str, path: str
) -> None:
    token = await token_only(logged_in)
    response = await logged_in.request(method, path, headers=bearer(token))
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_token_is_stored_as_hash_with_interpret_scope(
    logged_in: httpx.AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    token = await issue(logged_in)
    async with sessions() as session:
        row = (await session.scalars(select(ExtensionTokenRow))).one()
    assert row.token_hash == hashlib.sha256(token.encode()).hexdigest()
    assert (row.user_id, row.scope) == (USER, "interpret:read")


async def test_issuing_token_drops_expired_ones(
    logged_in: httpx.AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    await issue(logged_in)
    await expire_tokens(sessions)
    token = await issue(logged_in)
    async with sessions() as session:
        hashes = (await session.scalars(select(ExtensionTokenRow.token_hash))).all()
    assert hashes == [hashlib.sha256(token.encode()).hexdigest()]


async def test_page_text_is_journaled_as_hash_only(
    logged_in: httpx.AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    page = {"type": "page", "url": "https://news.example/rate", "text": "\n".join(PAGE_LINES)}
    response = await logged_in.post("/interpret", json={**interpret_body(), "action_context": page})
    assert response.status_code == status.HTTP_200_OK
    async with sessions() as session:
        row = (await session.execute(text("SELECT * FROM gateway_calls"))).one()
    journaled = " ".join(str(value) for value in row)
    assert not any(line in journaled for line in PAGE_LINES)
    assert len(row.context_hash) == 64
