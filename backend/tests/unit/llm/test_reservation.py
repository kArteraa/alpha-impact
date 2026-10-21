import asyncio

import httpx
import pytest

from apps.services import llm
from apps.services.llm.errors import ModelUnavailable
from shared.config.settings import Settings
from shared.contracts.errors import BudgetExceeded
from shared.contracts.ports import LLMGateway
from shared.di.container import Container
from tests.unit.llm.fakes import TODAY, MemoryStore, ModelServer, Usage, make_gateway


def spent(store: MemoryStore, cost_rub: float) -> None:
    store.add(Usage(TODAY, "interpret", "z-ai/glm-5.3-flash", 0, 0, cost_rub))


def slow_client(server: ModelServer) -> httpx.AsyncClient:
    async def handle(request: httpx.Request) -> httpx.Response:
        await asyncio.sleep(0.05)
        return server.handle(request)

    return httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="https://llm.example/v1"
    )


async def test_concurrent_calls_at_the_limit_let_only_one_through() -> None:
    store = MemoryStore()
    spent(store, 449.5)
    server = ModelServer()
    gateway = make_gateway(slow_client(server), store, call_reserve_rub=1.0)
    results = await asyncio.gather(
        *(gateway.complete("interpret", "sys", f"usr {n}") for n in range(5)),
        return_exceptions=True,
    )
    assert sum(not isinstance(result, BaseException) for result in results) == 1
    assert sum(isinstance(result, BudgetExceeded) for result in results) == 4
    assert len(server.requests) == 1


async def test_reservation_is_held_during_the_call() -> None:
    store = MemoryStore()
    seen: list[list[float]] = []
    server = ModelServer()
    inner = server.handle

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append([usage.cost_rub for usage in store.usages])
        return inner(request)

    http = httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="https://llm.example/v1"
    )
    await make_gateway(http, store, call_reserve_rub=2.5).complete("interpret", "sys", "usr")
    assert seen == [[2.5]]


async def test_reservation_is_replaced_by_the_actual_cost() -> None:
    store = MemoryStore()
    gateway = make_gateway(
        ModelServer(tokens_in=1000, tokens_out=500, cost_rub=0.07).http_client(), store
    )
    await gateway.complete("interpret", "sys", "usr")
    assert [(u.tokens_in, u.tokens_out, u.cost_rub) for u in store.usages] == [
        (1000, 500, pytest.approx(0.07))
    ]


async def test_charged_answer_without_token_counts_keeps_its_cost() -> None:
    store = MemoryStore()
    server = ModelServer(tokens_in=0, tokens_out=0, cost_rub=0.02)
    await make_gateway(server.http_client(), store).complete("interpret", "sys", "usr")
    assert [(u.tokens_in, u.cost_rub) for u in store.usages] == [(0, 0.02)]


async def test_unavailable_model_releases_the_reservation() -> None:
    store = MemoryStore()
    gateway = make_gateway(ModelServer(status=503).http_client(), store)
    with pytest.raises(ModelUnavailable):
        await gateway.complete("interpret", "sys", "usr")
    assert store.usages == []
    assert await gateway.budget_left_rub() == pytest.approx(450.0)


async def test_unexpected_failure_releases_the_reservation() -> None:
    store = MemoryStore()

    def handle(request: httpx.Request) -> httpx.Response:
        raise RuntimeError("boom")

    http = httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="https://llm.example/v1"
    )
    with pytest.raises(RuntimeError):
        await make_gateway(http, store).complete("interpret", "sys", "usr")
    assert store.usages == []


async def test_cancelled_call_releases_the_reservation() -> None:
    store = MemoryStore()
    started = asyncio.Event()

    async def handle(request: httpx.Request) -> httpx.Response:
        started.set()
        await asyncio.sleep(10)
        return httpx.Response(200)

    http = httpx.AsyncClient(
        transport=httpx.MockTransport(handle), base_url="https://llm.example/v1"
    )
    call = asyncio.create_task(make_gateway(http, store).complete("interpret", "sys", "usr"))
    await started.wait()
    call.cancel()
    with pytest.raises(asyncio.CancelledError):
        await call
    assert store.usages == []


async def test_closing_the_container_closes_the_http_client(
    settings_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    http = httpx.AsyncClient()
    monkeypatch.setattr(llm, "build_http_client", lambda settings: http)
    container = Container()
    container.register(Settings, lambda _: Settings(_env_file=None))
    container.register(llm.async_sessionmaker, lambda _: llm.async_sessionmaker())
    llm.register(container)
    container.resolve(LLMGateway)
    await container.aclose()
    assert http.is_closed
