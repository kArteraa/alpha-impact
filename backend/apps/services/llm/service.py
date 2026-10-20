import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

from pydantic import BaseModel, ValidationError

from apps.services.llm.catalog import ModelCatalog
from apps.services.llm.client import ModelClient
from apps.services.llm.errors import ModelOutputInvalid, ModelUnavailable
from apps.services.llm.store import Usage, UsageStore
from shared.contracts.errors import BudgetExceeded

EMBED_TASK = "embed"


def pydantic_schema(schema: type | None) -> type[BaseModel] | None:
    if schema is None or issubclass(schema, BaseModel):
        return schema
    raise TypeError(f"structured output needs a Pydantic model, got {schema.__name__}")


def response_format(schema: type[BaseModel] | None) -> dict[str, Any] | None:
    if schema is None:
        return None
    return {
        "type": "json_schema",
        "json_schema": {"name": schema.__name__, "schema": schema.model_json_schema()},
    }


def cache_key(*parts: object) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def parse(content: str, schema: type[BaseModel] | None) -> object:
    if schema is None:
        return content
    try:
        return schema.model_validate_json(content)
    except ValidationError as error:
        raise ModelOutputInvalid(f"answer does not match {schema.__name__}") from error


class ModelGateway:
    def __init__(
        self,
        catalog: ModelCatalog,
        client: ModelClient,
        store: UsageStore,
        daily_budget_rub: float,
        reserve_share: float,
        today: Callable[[], date],
    ) -> None:
        self._catalog = catalog
        self._client = client
        self._store = store
        self._spendable_rub = daily_budget_rub * (1 - reserve_share)
        self._today = today

    async def complete(
        self, task: str, system: str, user: str, schema: type | None = None
    ) -> tuple[object, int, int]:
        output_schema = pydantic_schema(schema)
        output_format = response_format(output_schema)
        model = self._catalog.route(task)
        key = cache_key(task, model, system, user, output_format)
        cached = await self._store.cached(key)
        if cached is not None:
            return parse(cached, output_schema), 0, 0
        await self._ensure_budget()
        completion = await self._charged(
            task, model, lambda: self._client.chat(model, system, user, output_format)
        )
        await self._spend(task, model, completion.tokens_in, completion.tokens_out)
        if not completion.content:
            raise ModelOutputInvalid(f"model {model} returned an empty answer")
        result = parse(completion.content, output_schema)
        await self._store.remember(key, completion.content)
        return result, completion.tokens_in, completion.tokens_out

    async def embed(self, text: str) -> list[float]:
        model = self._catalog.embedding_model
        key = cache_key(EMBED_TASK, model, text)
        cached = await self._store.cached(key)
        if cached is not None:
            vector: list[float] = json.loads(cached)
            return vector
        await self._ensure_budget()
        embedding = await self._charged(EMBED_TASK, model, lambda: self._client.embed(model, text))
        await self._spend(EMBED_TASK, model, embedding.tokens, 0)
        await self._store.remember(key, json.dumps(embedding.vector))
        return embedding.vector

    async def budget_left_rub(self) -> float:
        spent = await self._store.spent_rub(self._today())
        return max(0.0, self._spendable_rub - spent)

    async def _charged[T](self, task: str, model: str, call: Callable[[], Awaitable[T]]) -> T:
        try:
            return await call()
        except ModelUnavailable as error:
            if error.tokens_in or error.tokens_out:
                await self._spend(task, model, error.tokens_in, error.tokens_out)
            raise

    async def _ensure_budget(self) -> None:
        if await self.budget_left_rub() <= 0:
            raise BudgetExceeded(f"daily LLM budget of {self._spendable_rub:.2f} RUB is spent")

    async def _spend(self, task: str, model: str, tokens_in: int, tokens_out: int) -> None:
        cost = self._catalog.cost_rub(model, tokens_in, tokens_out)
        usage = Usage(self._today(), task, model, tokens_in, tokens_out, cost)
        await self._store.record(usage)
