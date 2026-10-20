import hashlib
import json
from collections.abc import Awaitable, Callable
from datetime import date
from typing import Any

from pydantic import BaseModel, ValidationError

from apps.services.llm.catalog import ModelCatalog
from apps.services.llm.client import ModelClient
from apps.services.llm.errors import (
    CacheNotWritten,
    ModelOutputInvalid,
    ModelUnavailable,
    UsageNotRecorded,
)
from apps.services.llm.store import UsageStore
from shared.contracts.errors import BudgetExceeded

EMBED_TASK = "embed"
REASONING_OFF = "reasoning_off"


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


def answer_text(content: str | None, model: str) -> str:
    if not content:
        raise ModelOutputInvalid(f"model {model} returned an empty answer")
    return content


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
        call_reserve_rub: float,
        today: Callable[[], date],
    ) -> None:
        self._catalog = catalog
        self._client = client
        self._store = store
        self._spendable_rub = daily_budget_rub * (1 - reserve_share)
        self._call_reserve_rub = call_reserve_rub
        self._today = today

    async def complete(
        self, task: str, system: str, user: str, schema: type | None = None
    ) -> tuple[object, int, int]:
        output_schema = pydantic_schema(schema)
        output_format = response_format(output_schema)
        model = self._catalog.route(task)
        reasoning = self._catalog.reasoning(task)
        parts = (task, model, system, user, output_format)
        key = cache_key(*parts) if reasoning else cache_key(*parts, REASONING_OFF)
        cached = await self._store.cached(key)
        if cached is not None:
            return parse(cached, output_schema), 0, 0
        reservation = await self._reserve(task, model)
        completion = await self._called(
            reservation,
            model,
            lambda: self._client.chat(model, system, user, output_format, reasoning),
        )
        tokens = (completion.tokens_in, completion.tokens_out)
        try:
            content = answer_text(completion.content, model)
            result = parse(content, output_schema)
        except ModelOutputInvalid:
            await self._record(reservation, model, *tokens)
            raise
        await self._remembered(reservation, model, key, content, tokens)
        return result, *tokens

    async def embed(self, text: str) -> list[float]:
        model = self._catalog.embedding_model
        key = cache_key(EMBED_TASK, model, text)
        cached = await self._store.cached(key)
        if cached is not None:
            vector: list[float] = json.loads(cached)
            return vector
        reservation = await self._reserve(EMBED_TASK, model)
        embedding = await self._called(reservation, model, lambda: self._client.embed(model, text))
        tokens = (embedding.tokens, 0)
        await self._remembered(reservation, model, key, json.dumps(embedding.vector), tokens)
        return embedding.vector

    async def budget_left_rub(self) -> float:
        spent = await self._store.spent_rub(self._today())
        return max(0.0, self._spendable_rub - spent)

    async def _reserve(self, task: str, model: str) -> int:
        reservation = await self._store.reserve(
            self._today(), task, model, self._call_reserve_rub, self._spendable_rub
        )
        if reservation is None:
            raise BudgetExceeded(f"daily LLM budget of {self._spendable_rub:.2f} RUB is spent")
        return reservation

    async def _called[T](self, reservation: int, model: str, call: Callable[[], Awaitable[T]]) -> T:
        try:
            return await call()
        except ModelUnavailable as error:
            await self._record(reservation, model, error.tokens_in, error.tokens_out)
            raise
        except BaseException:
            await self._store.settle(reservation, 0, 0, 0.0)
            raise

    async def _remembered(
        self, reservation: int, model: str, key: str, content: str, tokens: tuple[int, int]
    ) -> None:
        try:
            await self._store.remember(key, content)
        except Exception as error:
            await self._record(reservation, model, *tokens)
            raise CacheNotWritten(f"answer of reservation {reservation} is not cached") from error
        await self._record(reservation, model, *tokens)

    async def _record(self, reservation: int, model: str, tokens_in: int, tokens_out: int) -> None:
        cost = self._catalog.cost_rub(model, tokens_in, tokens_out)
        try:
            await self._store.settle(reservation, tokens_in, tokens_out, cost)
        except Exception as error:
            raise UsageNotRecorded(f"usage of reservation {reservation} is not recorded") from error
