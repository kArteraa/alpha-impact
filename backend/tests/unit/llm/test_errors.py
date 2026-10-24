import httpx
import pytest
from pydantic import BaseModel, ValidationError

from apps.services.llm.errors import ModelOutputInvalid, ModelUnavailable
from shared.contracts.errors import ChargedModelError, DomainError
from tests.unit.llm.fakes import MemoryStore, ModelServer, make_gateway


class Verdict(BaseModel):
    ok: bool
    reason: str


@pytest.mark.parametrize(
    "server",
    [
        ModelServer(status=500),
        ModelServer(status=429),
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


async def test_timeout_keeps_the_reservation_because_the_proxy_may_bill_it() -> None:
    store = MemoryStore()
    server = ModelServer(failure=httpx.ReadTimeout("timed out"))
    gateway = make_gateway(server.http_client(), store, call_reserve_rub=1.0)
    with pytest.raises(ModelUnavailable) as raised:
        await gateway.complete("interpret", "sys", "usr")
    assert isinstance(raised.value.__cause__, httpx.TimeoutException)
    assert [(u.tokens_in, u.cost_rub) for u in store.usages] == [(0, 1.0)]
    assert isinstance(raised.value, ChargedModelError)
    assert (raised.value.tokens_in, raised.value.cost_rub) == (0, 1.0)
    assert store.cache == {}


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
USAGE = {"prompt_tokens": 1200, "completion_tokens": 300, "cost": 0.4}
TOKENS = {"prompt_tokens": 1200, "completion_tokens": 300}


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
    with pytest.raises(ModelUnavailable) as raised:
        await gateway.complete("interpret", "sys", "usr")
    assert [(u.task, u.tokens_in, u.tokens_out, u.cost_rub) for u in store.usages] == [
        ("interpret", 1200, 300, 0.4)
    ]
    assert isinstance(raised.value, ChargedModelError)
    assert (raised.value.tokens_in, raised.value.tokens_out, raised.value.cost_rub) == (
        1200,
        300,
        0.4,
    )
    assert store.cache == {}


@pytest.mark.parametrize(
    "usage",
    [
        TOKENS,
        {**TOKENS, "cost": "0.4"},
        {**TOKENS, "cost": -1},
        {**TOKENS, "cost": True},
    ],
)
async def test_answer_without_cost_is_unavailable_and_keeps_the_reservation(
    usage: dict[str, object],
) -> None:
    store = MemoryStore()
    payload = {"choices": [{"message": {"content": "ok"}}], "usage": usage}
    gateway = make_gateway(ModelServer(payload=payload).http_client(), store, call_reserve_rub=1.0)
    with pytest.raises(ModelUnavailable):
        await gateway.complete("interpret", "sys", "usr")
    assert [(u.tokens_in, u.cost_rub) for u in store.usages] == [(0, 1.0)]
    assert store.cache == {}


@pytest.mark.parametrize("cost", ["NaN", "Infinity"])
async def test_non_finite_cost_is_unavailable_and_keeps_the_reservation(cost: str) -> None:
    store = MemoryStore()
    body = (
        '{"choices": [{"message": {"content": "ok"}}], '
        f'"usage": {{"prompt_tokens": 1200, "completion_tokens": 300, "cost": {cost}}}}}'
    )
    gateway = make_gateway(ModelServer(payload=body).http_client(), store, call_reserve_rub=1.0)
    with pytest.raises(ModelUnavailable):
        await gateway.complete("interpret", "sys", "usr")
    assert [(u.tokens_in, u.cost_rub) for u in store.usages] == [(0, 1.0)]


@pytest.mark.parametrize(
    "content",
    [[{"type": "text", "text": "ok"}], 42, {"text": "ok"}, True],
)
@pytest.mark.parametrize("schema", [None, Verdict])
async def test_non_text_content_is_unavailable_but_charged(
    content: object, schema: type | None
) -> None:
    store = MemoryStore()
    payload = {"choices": [{"message": {"content": content}}], "usage": USAGE}
    gateway = make_gateway(ModelServer(payload=payload).http_client(), store)
    with pytest.raises(ModelUnavailable):
        await gateway.complete("interpret", "sys", "usr", schema)
    assert [(u.tokens_in, u.tokens_out) for u in store.usages] == [(1200, 300)]
    assert store.cache == {}


@pytest.mark.parametrize(
    "usage",
    [
        {"prompt_tokens": "100", "completion_tokens": 3, "cost": 0.4},
        {"prompt_tokens": 100, "completion_tokens": -1, "cost": 0.4},
        {"prompt_tokens": True, "completion_tokens": 3, "cost": 0.4},
        {"prompt_tokens": 1.5, "completion_tokens": 3, "cost": 0.4},
    ],
)
async def test_malformed_token_counts_are_unavailable_but_the_cost_is_charged(
    usage: dict[str, object],
) -> None:
    store = MemoryStore()
    payload = {"choices": [{"message": {"content": "ok"}}], "usage": usage}
    gateway = make_gateway(ModelServer(payload=payload).http_client(), store)
    with pytest.raises(ModelUnavailable):
        await gateway.complete("interpret", "sys", "usr")
    assert [usage.cost_rub for usage in store.usages] == [0.4]
    assert store.cache == {}


async def test_invalid_answer_carries_charged_usage() -> None:
    store = MemoryStore()
    server = ModelServer(content="not json", tokens_in=900, tokens_out=100, cost_rub=0.12)
    gateway = make_gateway(server.http_client(), store)
    with pytest.raises(ChargedModelError) as raised:
        await gateway.complete("critic", "sys", "usr", Verdict)
    usage = store.usages[0]
    assert (raised.value.tokens_in, raised.value.tokens_out, raised.value.cost_rub) == (
        usage.tokens_in,
        usage.tokens_out,
        usage.cost_rub,
    )


async def test_schema_error_names_fields_without_values() -> None:
    gateway = make_gateway(ModelServer(content='{"ok": "maybe"}').http_client(), MemoryStore())
    with pytest.raises(ModelOutputInvalid) as raised:
        await gateway.complete("critic", "sys", "usr", Verdict)
    assert "ok" in str(raised.value)
    assert "maybe" not in str(raised.value)
