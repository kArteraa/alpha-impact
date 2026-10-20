import pytest
from pydantic import BaseModel

from apps.services.llm.errors import CacheNotWritten, UsageNotRecorded
from shared.contracts.errors import DomainError
from tests.unit.llm.fakes import MemoryStore, ModelServer, make_gateway


class Verdict(BaseModel):
    ok: bool


class BrokenSettleStore(MemoryStore):
    async def settle(
        self, reservation: int, tokens_in: int, tokens_out: int, cost_rub: float
    ) -> None:
        raise RuntimeError("database is down")


async def test_paid_answer_is_cached_when_usage_cannot_be_recorded() -> None:
    server = ModelServer(content='{"ok": true}')
    store = BrokenSettleStore()
    gateway = make_gateway(server.http_client(), store, call_reserve_rub=1.0)
    with pytest.raises(UsageNotRecorded) as raised:
        await gateway.complete("critic", "sys", "usr", Verdict)
    assert isinstance(raised.value, DomainError)
    assert isinstance(raised.value.__cause__, RuntimeError)
    assert len(store.cache) == 1
    assert [usage.cost_rub for usage in store.usages] == [1.0]
    assert await gateway.complete("critic", "sys", "usr", Verdict) == (Verdict(ok=True), 0, 0)
    assert len(server.requests) == 1


async def test_paid_embedding_is_cached_when_usage_cannot_be_recorded() -> None:
    server = ModelServer()
    store = BrokenSettleStore()
    gateway = make_gateway(server.http_client(), store)
    with pytest.raises(UsageNotRecorded):
        await gateway.embed("text")
    assert await gateway.embed("text") == [0.1, 0.2, 0.3]
    assert len(server.requests) == 1


async def test_invalid_answer_with_unrecorded_usage_is_not_cached() -> None:
    store = BrokenSettleStore()
    gateway = make_gateway(ModelServer(content="not json").http_client(), store)
    with pytest.raises(UsageNotRecorded):
        await gateway.complete("critic", "sys", "usr", Verdict)
    assert store.cache == {}


class BrokenCacheStore(MemoryStore):
    async def remember(self, key: str, content: str) -> None:
        raise RuntimeError("database is down")


async def test_answer_charged_as_fact_when_cache_cannot_be_written() -> None:
    server = ModelServer(content='{"ok": true}', tokens_in=1000, tokens_out=500)
    store = BrokenCacheStore()
    gateway = make_gateway(server.http_client(), store, call_reserve_rub=1.0)
    with pytest.raises(CacheNotWritten) as raised:
        await gateway.complete("critic", "sys", "usr", Verdict)
    assert isinstance(raised.value, DomainError)
    assert isinstance(raised.value.__cause__, RuntimeError)
    assert [(usage.tokens_in, usage.tokens_out) for usage in store.usages] == [(1000, 500)]


async def test_embedding_charged_as_fact_when_cache_cannot_be_written() -> None:
    server = ModelServer(tokens_in=10)
    store = BrokenCacheStore()
    gateway = make_gateway(server.http_client(), store, call_reserve_rub=1.0)
    with pytest.raises(CacheNotWritten):
        await gateway.embed("text")
    assert [usage.tokens_in for usage in store.usages] == [10]
