import json
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import date
from typing import Any

import httpx

from apps.services.llm.catalog import ModelCatalog
from apps.services.llm.client import ModelClient
from apps.services.llm.embedder import EmbedderSpec, TextEmbedder, load_spec
from apps.services.llm.service import ModelGateway
from apps.services.llm.store import UsageStore
from shared.config.embedding import EMBEDDING_DIMENSION
from tests.unit.conftest import SETTINGS_ENV

TODAY = date(2026, 10, 20)
ROUTES = {
    task: SETTINGS_ENV[f"MODEL_{task.upper()}"]
    for task in ("annotate", "extract", "interpret", "critic", "followup")
}
ALLOWED = frozenset(ROUTES.values())
TIMEOUTS = {"annotate": 8.0, "extract": 8.0, "interpret": 12.0, "critic": 8.0, "followup": 12.0}
SPEC = load_spec()
VECTOR = [0.1] * EMBEDDING_DIMENSION


class CountingEmbedder:
    def __init__(self, spec: EmbedderSpec = SPEC) -> None:
        self.spec = spec
        self.calls: list[str] = []

    def encode(self, text: str) -> list[float]:
        self.calls.append(text)
        return list(VECTOR)


@dataclass(frozen=True)
class Usage:
    day: date
    task: str
    model: str
    tokens_in: int
    tokens_out: int
    cost_rub: float


class MemoryStore:
    def __init__(self) -> None:
        self.cache: dict[str, str] = {}
        self.rows: dict[int, Usage] = {}

    @property
    def usages(self) -> list[Usage]:
        return list(self.rows.values())

    def add(self, usage: Usage) -> None:
        self.rows[len(self.rows) + 1000] = usage

    async def cached(self, key: str) -> str | None:
        return self.cache.get(key)

    async def remember(self, key: str, content: str) -> None:
        self.cache[key] = content

    async def reserve(
        self, day: date, task: str, model: str, amount_rub: float, spendable_rub: float
    ) -> int | None:
        if await self.spent_rub(day) >= spendable_rub:
            return None
        reservation = max(self.rows, default=0) + 1
        self.rows[reservation] = Usage(day, task, model, 0, 0, amount_rub)
        return reservation

    async def settle(
        self, reservation: int, tokens_in: int, tokens_out: int, cost_rub: float
    ) -> None:
        if tokens_in == 0 and tokens_out == 0 and cost_rub == 0:
            del self.rows[reservation]
            return
        self.rows[reservation] = replace(
            self.rows[reservation], tokens_in=tokens_in, tokens_out=tokens_out, cost_rub=cost_rub
        )

    async def spent_rub(self, day: date) -> float:
        return sum(usage.cost_rub for usage in self.usages if usage.day == day)


class ModelServer:
    def __init__(
        self,
        content: str | None = "ok",
        tokens_in: int = 1000,
        tokens_out: int = 500,
        cost_rub: float = 0.25,
        status: int = 200,
        failure: httpx.HTTPError | None = None,
        payload: object = None,
    ) -> None:
        self.payload = payload
        self.content = content
        self.status = status
        self.failure = failure
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.cost_rub = cost_rub
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.failure is not None:
            raise self.failure
        if self.status != 200:
            return httpx.Response(self.status, json={"error": "unavailable"})
        if isinstance(self.payload, str):
            return httpx.Response(200, text=self.payload)
        if self.payload is not None:
            return httpx.Response(200, json=self.payload)
        usage = {
            "prompt_tokens": self.tokens_in,
            "completion_tokens": self.tokens_out,
            "cost": self.cost_rub,
        }
        body = {"choices": [{"message": {"content": self.content}}], "usage": usage}
        return httpx.Response(200, json=body)

    def body(self, index: int = -1) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(self.requests[index].content)
        return loaded

    def http_client(self) -> httpx.AsyncClient:
        transport = httpx.MockTransport(self.handle)
        return httpx.AsyncClient(transport=transport, base_url="https://llm.example/v1")


def make_gateway(
    http: httpx.AsyncClient,
    store: UsageStore,
    daily_budget_rub: float = 500.0,
    reserve_share: float = 0.1,
    call_reserve_rub: float = 1.0,
    allowed: frozenset[str] = ALLOWED,
    today: Callable[[], date] = lambda: TODAY,
    embedder: TextEmbedder | None = None,
    reasoning_off: frozenset[str] = frozenset(),
) -> ModelGateway:
    return ModelGateway(
        catalog=ModelCatalog(allowed, ROUTES, reasoning_off, TIMEOUTS),
        client=ModelClient(http),
        embedder=embedder or CountingEmbedder(),
        store=store,
        daily_budget_rub=daily_budget_rub,
        reserve_share=reserve_share,
        call_reserve_rub=call_reserve_rub,
        today=today,
    )
