import pytest
from pydantic import BaseModel

from apps.services.llm.catalog import MODELS_PATH, load_models
from apps.services.llm.client import build_http_client
from apps.services.llm.embedder import LocalEmbedder
from apps.services.llm.service import cache_key, response_format
from shared.config.embedding import EMBEDDING_DIMENSION
from shared.config.settings import Settings
from tests.unit.llm.fakes import (
    ROUTES,
    SPEC,
    CountingEmbedder,
    MemoryStore,
    ModelServer,
    make_gateway,
)


class Verdict(BaseModel):
    ok: bool
    reason: str


async def test_structured_output_is_parsed_into_schema() -> None:
    server = ModelServer(content='{"ok": true, "reason": "sourced"}', tokens_in=12, tokens_out=7)
    result = await make_gateway(server.http_client(), MemoryStore()).complete(
        "critic", "sys", "usr", Verdict
    )
    assert result == (Verdict(ok=True, reason="sourced"), 12, 7, 0.25)


async def test_schema_is_sent_as_json_schema_response_format() -> None:
    server = ModelServer(content='{"ok": true, "reason": "r"}')
    await make_gateway(server.http_client(), MemoryStore()).complete(
        "critic", "sys", "usr", Verdict
    )
    response_format = server.body()["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "Verdict"
    assert response_format["json_schema"]["schema"] == Verdict.model_json_schema()


async def test_request_carries_routed_model_and_prompts() -> None:
    server = ModelServer()
    await make_gateway(server.http_client(), MemoryStore()).complete("annotate", "sys", "usr")
    body = server.body()
    assert server.requests[0].url.path == "/v1/chat/completions"
    assert body["model"] == "google/gemma-4-26b-a4b-it"
    assert body["temperature"] == 0
    assert body["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "usr"},
    ]
    assert "response_format" not in body


async def test_without_schema_returns_text() -> None:
    server = ModelServer(content="plain text", tokens_in=3, tokens_out=2)
    result = await make_gateway(server.http_client(), MemoryStore()).complete(
        "followup", "sys", "usr"
    )
    assert result == ("plain text", 3, 2, 0.25)


async def test_non_pydantic_schema_is_rejected() -> None:
    server = ModelServer()
    with pytest.raises(TypeError, match="dict"):
        await make_gateway(server.http_client(), MemoryStore()).complete(
            "critic", "sys", "usr", dict
        )
    assert server.requests == []


async def test_repeated_prompt_is_served_from_cache() -> None:
    server = ModelServer(content='{"ok": false, "reason": "r"}')
    store = MemoryStore()
    gateway = make_gateway(server.http_client(), store)
    await gateway.complete("critic", "sys", "usr", Verdict)
    result = await gateway.complete("critic", "sys", "usr", Verdict)
    assert result == (Verdict(ok=False, reason="r"), 0, 0, 0.0)
    assert len(server.requests) == 1
    assert len(store.usages) == 1


@pytest.mark.parametrize(
    ("task", "system", "user", "schema"),
    [
        ("annotate", "sys", "usr", None),
        ("critic", "other", "usr", None),
        ("critic", "sys", "other", None),
        ("critic", "sys", "usr", Verdict),
        ("interpret", "sys", "usr", None),
    ],
)
async def test_cache_key_covers_task_model_prompts_and_schema(
    task: str, system: str, user: str, schema: type | None
) -> None:
    server = ModelServer(content='{"ok": true, "reason": "r"}')
    gateway = make_gateway(server.http_client(), MemoryStore())
    await gateway.complete("critic", "sys", "usr")
    await gateway.complete(task, system, user, schema)
    assert len(server.requests) == 2


async def test_embed_returns_e5_vector_without_calling_the_proxy(e5: LocalEmbedder) -> None:
    server = ModelServer()
    store = MemoryStore()
    vector = await make_gateway(server.http_client(), store, embedder=e5).embed("цены на сталь")
    assert len(vector) == EMBEDDING_DIMENSION
    assert server.requests == []
    assert store.usages == []


async def test_repeated_embedding_is_served_from_cache() -> None:
    embedder = CountingEmbedder()
    gateway = make_gateway(ModelServer().http_client(), MemoryStore(), embedder=embedder)
    first = await gateway.embed("steel prices")
    assert await gateway.embed("steel prices") == first
    assert embedder.calls == ["steel prices"]


async def test_other_model_revision_misses_the_cache() -> None:
    store = MemoryStore()
    newer = CountingEmbedder(SPEC.model_copy(update={"revision": "0" * 40}))
    await make_gateway(ModelServer().http_client(), store).embed("steel prices")
    await make_gateway(ModelServer().http_client(), store, embedder=newer).embed("steel prices")
    assert newer.calls == ["steel prices"]


def test_http_client_uses_shared_key_base_and_timeout(settings_env: dict[str, str]) -> None:
    client = build_http_client(Settings(_env_file=None))
    assert str(client.base_url) == "https://llm.example/v1/"
    assert client.headers["Authorization"] == "Bearer test-key"
    assert client.timeout.read == 8
    assert client.timeout.connect == 8


@pytest.mark.parametrize("task", ["extract", "followup"])
async def test_task_without_reasoning_asks_model_not_to_reason(task: str) -> None:
    server = ModelServer(content='{"ok": true, "reason": "r"}')
    gateway = make_gateway(
        server.http_client(),
        MemoryStore(),
        reasoning_off=load_models(MODELS_PATH).reasoning_off_tasks,
    )

    result = await gateway.complete(task, "sys", "usr", Verdict)
    await gateway.complete("critic", "sys", "usr", Verdict)

    assert result == (Verdict(ok=True, reason="r"), 1000, 500, 0.25)
    assert server.body(0)["model"] == ROUTES[task]
    assert server.body(0)["reasoning"] == {"enabled": False}
    assert "reasoning" not in server.body(1)


@pytest.mark.parametrize("task", ["extract", "followup"])
async def test_reasoning_switch_is_part_of_cache_key(task: str) -> None:
    server = ModelServer(content='{"ok": true, "reason": "r"}')
    store = MemoryStore()
    await make_gateway(server.http_client(), store).complete(task, "sys", "usr", Verdict)

    switched = make_gateway(
        server.http_client(),
        store,
        reasoning_off=load_models(MODELS_PATH).reasoning_off_tasks,
    )
    result = await switched.complete(task, "sys", "usr", Verdict)

    assert result == (Verdict(ok=True, reason="r"), 1000, 500, 0.25)
    assert len(server.requests) == 2
    assert await switched.complete(task, "sys", "usr", Verdict) == (
        Verdict(ok=True, reason="r"),
        0,
        0,
        0.0,
    )
    assert len(server.requests) == 2


async def test_cache_key_of_task_with_reasoning_is_unchanged() -> None:
    server = ModelServer(content='{"ok": true, "reason": "r"}')
    store = MemoryStore()
    key = cache_key("critic", ROUTES["critic"], "sys", "usr", response_format(Verdict))
    store.cache[key] = '{"ok": false, "reason": "cached"}'
    gateway = make_gateway(server.http_client(), store, reasoning_off=frozenset({"extract"}))

    result = await gateway.complete("critic", "sys", "usr", Verdict)

    assert result == (Verdict(ok=False, reason="cached"), 0, 0, 0.0)
    assert server.requests == []


async def test_complete_returns_call_cost_and_cache_hit_costs_nothing() -> None:
    server = ModelServer(content='{"ok": true, "reason": "r"}', cost_rub=0.37)
    store = MemoryStore()
    gateway = make_gateway(server.http_client(), store)

    first = await gateway.complete("critic", "sys", "usr", Verdict)
    second = await gateway.complete("critic", "sys", "usr", Verdict)

    assert (first[3], second[3]) == (0.37, 0.0)
    assert first[3] + second[3] == sum(usage.cost_rub for usage in store.usages)
