import httpx
import pytest
from pydantic import BaseModel, ValidationError

from apps.services.llm.errors import ModelOutputInvalid, ModelUnavailable
from shared.contracts.errors import DomainError
from tests.unit.llm.fakes import MemoryStore, ModelServer, make_gateway


class Verdict(BaseModel):
    ok: bool
    reason: str


@pytest.mark.parametrize(
    "server",
    [
        ModelServer(status=500),
        ModelServer(status=429),
        ModelServer(failure=httpx.ReadTimeout("timed out")),
        ModelServer(failure=httpx.ConnectError("refused")),
    ],
)
async def test_unreachable_model_raises_domain_error_without_charge(server: ModelServer) -> None:
    store = MemoryStore()
    with pytest.raises(ModelUnavailable) as raised:
        await make_gateway(server.http_client(), store).complete("interpret", "sys", "usr")
    assert isinstance(raised.value, DomainError)
    assert isinstance(raised.value.__cause__, httpx.HTTPError)
    assert store.usages == []
    assert store.cache == {}


async def test_unreachable_embedding_model_raises_domain_error() -> None:
    store = MemoryStore()
    with pytest.raises(ModelUnavailable):
        await make_gateway(ModelServer(status=503).http_client(), store).embed("text")
    assert store.usages == []


@pytest.mark.parametrize("content", [None, ""])
@pytest.mark.parametrize("schema", [None, Verdict])
async def test_empty_answer_is_charged_but_not_cached(
    content: str | None, schema: type | None
) -> None:
    store = MemoryStore()
    gateway = make_gateway(ModelServer(content=content).http_client(), store)
    with pytest.raises(ModelOutputInvalid) as raised:
        await gateway.complete("critic", "sys", "usr", schema)
    assert isinstance(raised.value, DomainError)
    assert len(store.usages) == 1
    assert store.cache == {}


@pytest.mark.parametrize("content", ["not json", '{"ok": "maybe"}'])
async def test_answer_outside_schema_is_charged_but_not_cached(content: str) -> None:
    store = MemoryStore()
    gateway = make_gateway(ModelServer(content=content).http_client(), store)
    with pytest.raises(ModelOutputInvalid) as raised:
        await gateway.complete("critic", "sys", "usr", Verdict)
    assert isinstance(raised.value, DomainError)
    assert isinstance(raised.value.__cause__, ValidationError)
    assert len(store.usages) == 1
    assert store.cache == {}


async def test_retry_after_invalid_answer_calls_the_model_again() -> None:
    server = ModelServer(content="not json")
    gateway = make_gateway(server.http_client(), MemoryStore())
    for _ in range(2):
        with pytest.raises(ModelOutputInvalid):
            await gateway.complete("critic", "sys", "usr", Verdict)
    assert len(server.requests) == 2


NOT_JSON = "<html>502 bad gateway</html>"
USAGE = {"prompt_tokens": 1200, "completion_tokens": 300}
EMBED_USAGE = {"prompt_tokens": 40}


@pytest.mark.parametrize(
    "payload",
    [
        NOT_JSON,
        {"choices": [{"message": {"content": "ok"}}]},
        {"choices": [], "usage": "broken"},
        ["not", "an", "object"],
    ],
)
async def test_broken_completion_without_usage_is_unavailable_and_not_charged(
    payload: object,
) -> None:
    store = MemoryStore()
    gateway = make_gateway(ModelServer(payload=payload).http_client(), store)
    with pytest.raises(ModelUnavailable) as raised:
        await gateway.complete("interpret", "sys", "usr")
    assert isinstance(raised.value, DomainError)
    assert store.usages == []
    assert store.cache == {}


@pytest.mark.parametrize(
    "payload",
    [
        {"choices": [], "usage": USAGE},
        {"choices": [{"message": {}}], "usage": USAGE},
        {"usage": USAGE},
    ],
)
async def test_broken_completion_with_usage_is_unavailable_but_charged(payload: object) -> None:
    store = MemoryStore()
    gateway = make_gateway(ModelServer(payload=payload).http_client(), store)
    with pytest.raises(ModelUnavailable):
        await gateway.complete("interpret", "sys", "usr")
    assert [(u.task, u.tokens_in, u.tokens_out) for u in store.usages] == [("interpret", 1200, 300)]
    assert store.cache == {}


@pytest.mark.parametrize(
    "payload",
    [
        NOT_JSON,
        {"data": [{"embedding": [0.1]}]},
        {"data": []},
    ],
)
async def test_broken_embedding_without_usage_is_unavailable_and_not_charged(
    payload: object,
) -> None:
    store = MemoryStore()
    gateway = make_gateway(ModelServer(payload=payload).http_client(), store)
    with pytest.raises(ModelUnavailable) as raised:
        await gateway.embed("text")
    assert isinstance(raised.value, DomainError)
    assert store.usages == []
    assert store.cache == {}


@pytest.mark.parametrize(
    "payload",
    [
        {"usage": EMBED_USAGE},
        {"data": [], "usage": EMBED_USAGE},
        {"data": [{}], "usage": EMBED_USAGE},
    ],
)
async def test_broken_embedding_with_usage_is_unavailable_but_charged(payload: object) -> None:
    store = MemoryStore()
    gateway = make_gateway(ModelServer(payload=payload).http_client(), store)
    with pytest.raises(ModelUnavailable):
        await gateway.embed("text")
    assert [(u.task, u.tokens_in, u.tokens_out) for u in store.usages] == [("embed", 40, 0)]
    assert store.cache == {}
