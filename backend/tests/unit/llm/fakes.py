import json
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx

from apps.services.llm.catalog import ModelCatalog, ModelPrice
from apps.services.llm.client import ModelClient
from apps.services.llm.service import ModelGateway
from apps.services.llm.store import Usage

TODAY = date(2026, 10, 20)
PRICE = ModelPrice(input_rub_per_1m=100.0, output_rub_per_1m=300.0)
ROUTES = {
    "annotate": "gemma-4-26b-a4b",
    "extract": "qwen3.6-35b-a3b",
    "interpret": "glm-5.3-flash",
    "critic": "glm-5.3-flash",
    "followup": "qwen3.6-35b-a3b",
}
EMBEDDING_MODEL = "tbd-embedding-model"
PRICES = {model: PRICE for model in [*ROUTES.values(), EMBEDDING_MODEL]}


class MemoryStore:
    def __init__(self) -> None:
        self.cache: dict[str, str] = {}
        self.usages: list[Usage] = []

    async def cached(self, key: str) -> str | None:
        return self.cache.get(key)

    async def remember(self, key: str, model: str, content: str) -> None:
        self.cache[key] = content

    async def record(self, usage: Usage) -> None:
        self.usages.append(usage)

    async def spent_rub(self, day: date) -> float:
        return sum(usage.cost_rub for usage in self.usages if usage.day == day)


class ModelServer:
    def __init__(self, content: str = "ok", tokens_in: int = 1000, tokens_out: int = 500) -> None:
        self.content = content
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.requests: list[httpx.Request] = []

    def handle(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        usage = {"prompt_tokens": self.tokens_in, "completion_tokens": self.tokens_out}
        if request.url.path.endswith("/embeddings"):
            body: dict[str, Any] = {
                "data": [{"embedding": [0.1, 0.2, 0.3]}],
                "usage": {"prompt_tokens": self.tokens_in, "total_tokens": self.tokens_in},
            }
        else:
            body = {"choices": [{"message": {"content": self.content}}], "usage": usage}
        return httpx.Response(200, json=body)

    def body(self, index: int = -1) -> dict[str, Any]:
        loaded: dict[str, Any] = json.loads(self.requests[index].content)
        return loaded

    def client_factory(self) -> Callable[[], httpx.AsyncClient]:
        transport = httpx.MockTransport(self.handle)
        return lambda: httpx.AsyncClient(transport=transport, base_url="https://llm.example/v1")


def make_gateway(
    server: ModelServer,
    store: MemoryStore,
    daily_budget_rub: float = 500.0,
    reserve_share: float = 0.1,
) -> ModelGateway:
    return ModelGateway(
        catalog=ModelCatalog(PRICES, ROUTES, EMBEDDING_MODEL),
        client=ModelClient(server.client_factory()),
        store=store,
        daily_budget_rub=daily_budget_rub,
        reserve_share=reserve_share,
        today=lambda: TODAY,
    )
