import pytest
from pydantic import BaseModel, ValidationError

from apps.services.llm.client import build_http_client
from shared.config.settings import Settings
from tests.unit.llm.fakes import MemoryStore, ModelServer, make_gateway


class Verdict(BaseModel):
    ok: bool
    reason: str


async def test_structured_output_is_parsed_into_schema() -> None:
    server = ModelServer(content='{"ok": true, "reason": "sourced"}', tokens_in=12, tokens_out=7)
    result = await make_gateway(server, MemoryStore()).complete("critic", "sys", "usr", Verdict)
    assert result == (Verdict(ok=True, reason="sourced"), 12, 7)


async def test_schema_is_sent_as_json_schema_response_format() -> None:
    server = ModelServer(content='{"ok": true, "reason": "r"}')
    await make_gateway(server, MemoryStore()).complete("critic", "sys", "usr", Verdict)
    response_format = server.body()["response_format"]
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["name"] == "Verdict"
    assert response_format["json_schema"]["schema"] == Verdict.model_json_schema()


async def test_request_carries_routed_model_and_prompts() -> None:
    server = ModelServer()
    await make_gateway(server, MemoryStore()).complete("annotate", "sys", "usr")
    body = server.body()
    assert server.requests[0].url.path == "/v1/chat/completions"
    assert body["model"] == "gemma-4-26b-a4b"
    assert body["temperature"] == 0
    assert body["messages"] == [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "usr"},
    ]
    assert "response_format" not in body


async def test_without_schema_returns_text() -> None:
    server = ModelServer(content="plain text", tokens_in=3, tokens_out=2)
    result = await make_gateway(server, MemoryStore()).complete("followup", "sys", "usr")
    assert result == ("plain text", 3, 2)


async def test_invalid_structured_output_raises_and_is_not_cached() -> None:
    server = ModelServer(content="not json")
    store = MemoryStore()
    gateway = make_gateway(server, store)
    with pytest.raises(ValidationError):
        await gateway.complete("critic", "sys", "usr", Verdict)
    assert store.cache == {}
    assert len(store.usages) == 1


async def test_non_pydantic_schema_is_rejected() -> None:
    server = ModelServer()
    with pytest.raises(TypeError, match="dict"):
        await make_gateway(server, MemoryStore()).complete("critic", "sys", "usr", dict)
    assert server.requests == []


async def test_repeated_prompt_is_served_from_cache() -> None:
    server = ModelServer(content='{"ok": false, "reason": "r"}')
    store = MemoryStore()
    gateway = make_gateway(server, store)
    await gateway.complete("critic", "sys", "usr", Verdict)
    result = await gateway.complete("critic", "sys", "usr", Verdict)
    assert result == (Verdict(ok=False, reason="r"), 0, 0)
    assert len(server.requests) == 1
    assert len(store.usages) == 1


@pytest.mark.parametrize(
    ("task", "system", "user", "schema"),
    [
        ("annotate", "sys", "usr", None),
        ("critic", "other", "usr", None),
        ("critic", "sys", "other", None),
        ("critic", "sys", "usr", Verdict),
    ],
)
async def test_cache_key_covers_model_prompts_and_schema(
    task: str, system: str, user: str, schema: type | None
) -> None:
    server = ModelServer(content='{"ok": true, "reason": "r"}')
    gateway = make_gateway(server, MemoryStore())
    await gateway.complete("critic", "sys", "usr")
    await gateway.complete(task, system, user, schema)
    assert len(server.requests) == 2


async def test_embed_returns_vector_and_charges_tokens() -> None:
    server = ModelServer(tokens_in=1000)
    store = MemoryStore()
    vector = await make_gateway(server, store).embed("steel prices")
    assert vector == [0.1, 0.2, 0.3]
    assert server.requests[0].url.path == "/v1/embeddings"
    assert server.body() == {"model": "tbd-embedding-model", "input": "steel prices"}
    assert store.usages[0].task == "embed"
    assert store.usages[0].cost_rub == pytest.approx(0.1)


async def test_repeated_embedding_is_served_from_cache() -> None:
    server = ModelServer()
    gateway = make_gateway(server, MemoryStore())
    await gateway.embed("steel prices")
    assert await gateway.embed("steel prices") == [0.1, 0.2, 0.3]
    assert len(server.requests) == 1


def test_http_client_uses_shared_key_base_and_timeout(settings_env: dict[str, str]) -> None:
    client = build_http_client(Settings(_env_file=None))
    assert str(client.base_url) == "https://llm.example/v1/"
    assert client.headers["Authorization"] == "Bearer test-key"
    assert client.timeout.read == 8
    assert client.timeout.connect == 8
