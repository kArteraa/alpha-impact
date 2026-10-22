from collections.abc import AsyncIterator

import httpx
import pytest
from fastapi import FastAPI, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from shared.contracts.ports import TraceStore
from shared.contracts.schemas import InterpretResponse, Trace
from shared.db.models import FeedbackRow, UserRow
from tests.integration.contracts.examples import CARD, TRACE

USER = "user_cfo_wholesale"
OTHER_USER = "user_owner_retail"


def owned_trace(trace_id: str, user_id: str, card_id: str) -> Trace:
    card = CARD.model_copy(update={"id": card_id, "trace_id": trace_id})
    return TRACE.model_copy(
        update={
            "id": trace_id,
            "request": TRACE.request.model_copy(update={"user_id": user_id}),
            "result": InterpretResponse(silent=False, cards=[card]),
        }
    )


MINE = owned_trace("trace-mine", USER, "card-mine")
FOREIGN = owned_trace("trace-foreign", OTHER_USER, "card-foreign")


@pytest.fixture
async def app(sessions: async_sessionmaker[AsyncSession]) -> AsyncIterator[FastAPI]:
    from main import create_app

    async with sessions() as session, session.begin():
        session.add_all(
            [UserRow(id=USER, name="Финансовый директор"), UserRow(id=OTHER_USER, name="Владелец")]
        )
    application = create_app()
    store = application.state.container.resolve(TraceStore)
    await store.save(MINE)
    await store.save(FOREIGN)
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


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", f"/trace/{MINE.id}", None),
        ("GET", "/metrics?since=2026-10-01", None),
        ("POST", "/feedback", {"card_id": "card-mine", "useful": True}),
    ],
)
async def test_trace_routes_require_session(
    client: httpx.AsyncClient, method: str, path: str, body: dict[str, object] | None
) -> None:
    response = await client.request(method, path, json=body)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED


async def test_own_trace_is_returned(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.get(f"/trace/{MINE.id}")
    assert response.status_code == status.HTTP_200_OK
    assert Trace.model_validate(response.json()) == MINE


async def test_foreign_trace_is_forbidden(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.get(f"/trace/{FOREIGN.id}")
    assert response.status_code == status.HTTP_403_FORBIDDEN


async def test_unknown_trace_is_not_found(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.get("/trace/missing")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_metrics_for_period(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.get(
        "/metrics", params={"since": TRACE.created_at.date().isoformat()}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["silent_share"] == 0.0
    assert set(response.json()) >= {"sourced_claims_share", "tokens_per_card", "cache_share"}


async def test_metrics_require_period(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.get("/metrics")
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


async def test_feedback_is_recorded_and_replaced(
    logged_in: httpx.AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    first = await logged_in.post(
        "/feedback", json={"card_id": "card-mine", "useful": True, "comment": "Полезно"}
    )
    second = await logged_in.post("/feedback", json={"card_id": "card-mine", "useful": False})
    assert (first.status_code, second.status_code) == (204, 204)
    async with sessions() as session:
        rows = (await session.scalars(select(FeedbackRow))).all()
    assert [(row.card_id, row.trace_id, row.useful, row.comment) for row in rows] == [
        ("card-mine", MINE.id, False, None)
    ]


@pytest.mark.parametrize(
    ("card_id", "code"),
    [("card-foreign", status.HTTP_403_FORBIDDEN), ("card-z", status.HTTP_404_NOT_FOUND)],
)
async def test_feedback_errors_map_to_http(
    logged_in: httpx.AsyncClient, card_id: str, code: int
) -> None:
    response = await logged_in.post("/feedback", json={"card_id": card_id, "useful": True})
    assert response.status_code == code


def test_openapi_matches_trace_contracts(app: FastAPI) -> None:
    openapi = app.openapi()
    paths = openapi["paths"]
    trace = paths["/trace/{trace_id}"]["get"]["responses"]["200"]["content"]["application/json"]
    assert trace["schema"]["$ref"].endswith("/Trace")
    feedback = paths["/feedback"]["post"]["requestBody"]["content"]["application/json"]
    body = feedback["schema"]["$ref"].rsplit("/", 1)[1]
    assert set(openapi["components"]["schemas"][body]["properties"]) == {
        "card_id",
        "useful",
        "comment",
    }
    query = [p for p in paths["/metrics"]["get"]["parameters"] if p["in"] == "query"]
    assert [(p["name"], p["required"]) for p in query] == [("since", True)]
