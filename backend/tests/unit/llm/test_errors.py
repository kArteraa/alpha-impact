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
USAGE = {"prompt_tokens": 1, "completion_tokens": 1}


@pytest.mark.parametrize(
    "payload",
    [
        NOT_JSON,
        {"choices": [{"message": {"content": "ok"}}]},
        {"choices": [], "usage": USAGE},
        {"choices": [{"message": {}}], "usage": USAGE},
        {"usage": USAGE},
        ["not", "an", "object"],
    ],
)
async def test_malformed_completion_envelope_is_model_unavailable(payload: object) -> None:
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
        NOT_JSON,
        {"usage": {"prompt_tokens": 1}},
        {"data": [], "usage": {"prompt_tokens": 1}},
        {"data": [{"embedding": [0.1]}]},
        {"data": [{}], "usage": {"prompt_tokens": 1}},
    ],
)
async def test_malformed_embedding_envelope_is_model_unavailable(payload: object) -> None:
    store = MemoryStore()
    gateway = make_gateway(ModelServer(payload=payload).http_client(), store)
    with pytest.raises(ModelUnavailable) as raised:
        await gateway.embed("text")
    assert isinstance(raised.value, DomainError)
    assert store.usages == []
    assert store.cache == {}
