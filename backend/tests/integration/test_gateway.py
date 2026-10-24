from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from shared.config.settings import Settings
from shared.contracts.errors import BudgetExceeded, ChargedModelError, DomainError
from shared.contracts.ports import HouseViewService, Interpreter
from shared.contracts.schemas import (
    Claim,
    ClaimType,
    InsightCard,
    InterpretRequest,
    InterpretResponse,
    SourceRef,
)
from shared.db.models import GatewayCallRow, UserClientRow, UserRow

USER = "user_cfo_wholesale"
OTHER_USER = "user_owner_retail"
COLLEAGUE = "user_treasurer_wholesale"
ROUTES = (
    ("POST", "/interpret"),
    ("GET", "/profile/{client_id}"),
    ("PATCH", "/profile/{client_id}/features/{name}"),
    ("GET", "/clients"),
    ("POST", "/feedback"),
    ("GET", "/trace/{trace_id}"),
    ("GET", "/reports/{source_doc}"),
    ("GET", "/metrics"),
    ("POST", "/auth/mock"),
    ("POST", "/auth/extension-token"),
)


class FakeInterpreter:
    def __init__(self) -> None:
        self.calls: list[InterpretRequest] = []
        self.error: Exception | None = None
        self.needs_review = False

    async def interpret(self, request: InterpretRequest) -> InterpretResponse:
        self.calls.append(request)
        if self.error is not None:
            raise self.error
        claim = Claim(
            text="Ставка снижена", type=ClaimType.FACT, source_ref=SourceRef(kind="news", id="n1")
        )
        card = InsightCard(
            id="c1",
            headline="Ставка",
            what_happened=[claim],
            why_for_you=[claim],
            consequences=[claim],
            actions=[claim],
            bank_view=[],
            basis=[claim.source_ref],
            significance=0.5,
            trace_id=f"trace-{len(self.calls)}",
            needs_review=self.needs_review,
        )
        return InterpretResponse(silent=False, cards=[card])


class FakeHouseView:
    def __init__(self) -> None:
        self.current = "v1"

    async def version(self) -> str:
        return self.current


@pytest.fixture
def interpreter() -> FakeInterpreter:
    return FakeInterpreter()


@pytest.fixture
def house_view() -> FakeHouseView:
    return FakeHouseView()


@pytest.fixture
async def app(
    sessions: async_sessionmaker[AsyncSession],
    interpreter: FakeInterpreter,
    house_view: FakeHouseView,
) -> AsyncIterator[FastAPI]:
    from main import create_app

    async with sessions() as session, session.begin():
        session.add_all(
            [
                UserRow(id=USER, name="Финансовый директор"),
                UserRow(id=OTHER_USER, name="Владелец"),
                UserRow(id=COLLEAGUE, name="Казначей"),
            ]
        )
        await session.flush()
        session.add_all(
            [
                UserClientRow(user_id=USER, client_id="U_1"),
                UserClientRow(user_id=USER, client_id="U_2"),
                UserClientRow(user_id=OTHER_USER, client_id="U_9"),
                UserClientRow(user_id=COLLEAGUE, client_id="U_1"),
            ]
        )
    application = create_app()
    application.state.container.register(Interpreter, lambda _: interpreter)
    application.state.container.register(HouseViewService, lambda _: house_view)
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


def interpret_body(
    client_id: str = "U_1", user_id: str = USER, amount: float = 100.0
) -> dict[str, Any]:
    return {
        "user_id": user_id,
        "client_id": client_id,
        "role": "cfo",
        "action_context": {"type": "payment", "beneficiary_id": "B_1", "amount": amount},
    }


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


async def test_unknown_session_is_rejected(client: httpx.AsyncClient) -> None:
    client.cookies.set("alfa_session", "nobody")
    assert (await client.get("/clients")).status_code == 401


async def test_clients_lists_bound_companies(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.get("/clients")
    assert response.status_code == 200
    assert sorted(response.json()) == ["U_1", "U_2"]


async def test_interpret_requires_session(
    client: httpx.AsyncClient, interpreter: FakeInterpreter
) -> None:
    assert (await client.post("/interpret", json=interpret_body())).status_code == 401
    assert interpreter.calls == []


async def test_interpret_for_foreign_client_is_forbidden(
    logged_in: httpx.AsyncClient, interpreter: FakeInterpreter
) -> None:
    response = await logged_in.post("/interpret", json=interpret_body(client_id="U_9"))
    assert response.status_code == 403
    assert interpreter.calls == []


async def test_interpret_for_another_user_is_forbidden(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.post("/interpret", json=interpret_body(user_id=OTHER_USER))
    assert response.status_code == 403


async def test_interpret_validates_request(logged_in: httpx.AsyncClient) -> None:
    body = interpret_body()
    body["action_context"] = {"type": "payment"}
    assert (await logged_in.post("/interpret", json=body)).status_code == 422


async def test_repeated_interpret_is_cached_without_interpreter(
    logged_in: httpx.AsyncClient, interpreter: FakeInterpreter
) -> None:
    first = await logged_in.post("/interpret", json=interpret_body())
    second = await logged_in.post("/interpret", json=interpret_body())
    assert first.status_code == 200
    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    assert second.json()["cards"] == first.json()["cards"]
    assert len(interpreter.calls) == 1


async def test_changed_context_or_house_view_misses_cache(
    logged_in: httpx.AsyncClient, interpreter: FakeInterpreter, house_view: FakeHouseView
) -> None:
    await logged_in.post("/interpret", json=interpret_body())
    other = await logged_in.post("/interpret", json=interpret_body(amount=200.0))
    house_view.current = "v2"
    renewed = await logged_in.post("/interpret", json=interpret_body())
    assert other.json()["cached"] is False
    assert renewed.json()["cached"] is False
    assert len(interpreter.calls) == 3


async def test_profile_correction_misses_cache(
    logged_in: httpx.AsyncClient, interpreter: FakeInterpreter
) -> None:
    await logged_in.post("/interpret", json=interpret_body())
    await logged_in.patch("/profile/U_1/features/industry_class", json={"value": "retail"})
    response = await logged_in.post("/interpret", json=interpret_body())
    assert response.json()["cached"] is False
    assert len(interpreter.calls) == 2


async def test_colleague_gets_own_trace_not_cached_one(
    logged_in: httpx.AsyncClient,
    interpreter: FakeInterpreter,
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    await logged_in.post("/interpret", json=interpret_body())
    await logged_in.post("/auth/mock", json={"user_id": COLLEAGUE})
    response = await logged_in.post("/interpret", json=interpret_body(user_id=COLLEAGUE))
    assert response.json()["cached"] is False
    assert response.json()["cards"][0]["trace_id"] == "trace-2"
    async with sessions() as session:
        rows = (await session.scalars(select(GatewayCallRow).order_by(GatewayCallRow.id))).all()
    assert [(row.user_id, row.trace_id) for row in rows] == [
        (USER, "trace-1"),
        (COLLEAGUE, "trace-2"),
    ]


async def test_needs_review_card_is_not_cached(
    logged_in: httpx.AsyncClient, interpreter: FakeInterpreter, engine: AsyncEngine
) -> None:
    interpreter.needs_review = True
    first = await logged_in.post("/interpret", json=interpret_body())
    second = await logged_in.post("/interpret", json=interpret_body())
    assert first.json()["cards"][0]["needs_review"] is True
    assert (first.json()["cached"], second.json()["cached"]) == (False, False)
    assert len(interpreter.calls) == 2
    async with engine.connect() as connection:
        rows = await connection.execute(text("SELECT count(*) FROM interpret_cache"))
    assert rows.scalar_one() == 0


async def test_expired_cache_entry_is_not_served(
    logged_in: httpx.AsyncClient, interpreter: FakeInterpreter, engine: AsyncEngine
) -> None:
    await logged_in.post("/interpret", json=interpret_body())
    age = Settings().CACHE_TTL_SECONDS + 1
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "UPDATE interpret_cache SET created_at = created_at - make_interval(secs => :age)"
            ),
            {"age": age},
        )
    response = await logged_in.post("/interpret", json=interpret_body())
    assert response.json()["cached"] is False
    assert len(interpreter.calls) == 2


async def test_interpret_calls_are_journaled(
    logged_in: httpx.AsyncClient, sessions: async_sessionmaker[AsyncSession]
) -> None:
    await logged_in.post("/interpret", json=interpret_body())
    await logged_in.post("/interpret", json=interpret_body())
    async with sessions() as session:
        rows = (await session.scalars(select(GatewayCallRow).order_by(GatewayCallRow.id))).all()
    assert [(row.user_id, row.client_id, row.action_type) for row in rows] == [
        (USER, "U_1", "payment"),
        (USER, "U_1", "payment"),
    ]
    assert [(row.trace_id, row.cached, row.outcome) for row in rows] == [
        ("trace-1", False, "ok"),
        ("trace-1", True, "ok"),
    ]
    assert len(rows[0].context_hash) == 64


@pytest.mark.parametrize(
    ("error", "status_code"),
    [
        (DomainError("bad draft"), 422),
        (BudgetExceeded("no budget"), 503),
        (ChargedModelError("model API timed out"), 503),
    ],
)
async def test_interpreter_errors_map_to_http(
    logged_in: httpx.AsyncClient, interpreter: FakeInterpreter, error: Exception, status_code: int
) -> None:
    interpreter.error = error
    response = await logged_in.post("/interpret", json=interpret_body())
    assert response.status_code == status_code


async def test_profile_of_own_client(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.get("/profile/U_1")
    assert response.status_code == 200
    assert response.json()["client_id"] == "U_1"


async def test_profile_of_foreign_client_is_forbidden(logged_in: httpx.AsyncClient) -> None:
    assert (await logged_in.get("/profile/U_9")).status_code == 403


async def test_profile_requires_session(client: httpx.AsyncClient) -> None:
    assert (await client.get("/profile/U_1")).status_code == 401


async def test_patch_feature_saves_user_correction(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.patch(
        "/profile/U_1/features/industry_class", json={"value": "retail"}
    )
    assert response.status_code == 200
    feature = response.json()["features"]["industry_class"]
    assert (feature["value"], feature["source"]) == ("retail", "user")


async def test_patch_unknown_feature_is_not_found(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.patch("/profile/U_1/features/unknown", json={"value": "x"})
    assert response.status_code == 404


async def test_patch_foreign_client_is_forbidden(logged_in: httpx.AsyncClient) -> None:
    response = await logged_in.patch(
        "/profile/U_9/features/industry_class", json={"value": "retail"}
    )
    assert response.status_code == 403


def schema_ref(operation: dict[str, Any], *path: str) -> str:
    node: Any = operation
    for key in path:
        node = node[key]
    return str(node["$ref"]).rsplit("/", 1)[1]


def test_openapi_matches_contracts(app: FastAPI) -> None:
    openapi = app.openapi()
    paths = openapi["paths"]
    served = {(method.upper(), path) for path, item in paths.items() for method in item}
    assert served - {("GET", "/health")} == set(ROUTES)
    json_body = ("requestBody", "content", "application/json", "schema")
    ok_body = ("responses", "200", "content", "application/json", "schema")
    interpret = paths["/interpret"]["post"]
    assert schema_ref(interpret, *json_body) == "InterpretRequest"
    assert schema_ref(interpret, *ok_body) == "InterpretResponse"
    assert schema_ref(paths["/profile/{client_id}"]["get"], *ok_body) == "ClientProfile"
    patch = paths["/profile/{client_id}/features/{name}"]["patch"]
    assert schema_ref(patch, *ok_body) == "ClientProfile"
    correction = schema_ref(patch, *json_body)
    assert set(openapi["components"]["schemas"][correction]["properties"]) == {"value"}
    clients = paths["/clients"]["get"]["responses"]["200"]["content"]["application/json"]
    assert clients["schema"]["items"]["type"] == "string"
    report = paths["/reports/{source_doc}"]["get"]["responses"]["200"]["content"]
    assert list(report) == ["application/pdf"]
    token = schema_ref(paths["/auth/extension-token"]["post"], *ok_body)
    assert set(openapi["components"]["schemas"][token]["properties"]) == {"token", "expires_at"}
