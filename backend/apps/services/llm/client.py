from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from shared.config.settings import Settings

ClientFactory = Callable[[], httpx.AsyncClient]


@dataclass(frozen=True)
class Completion:
    content: str
    tokens_in: int
    tokens_out: int


@dataclass(frozen=True)
class Embedding:
    vector: list[float]
    tokens: int


class ModelClient:
    def __init__(self, client_factory: ClientFactory) -> None:
        self._client_factory = client_factory

    async def chat(
        self, model: str, system: str, user: str, response_format: dict[str, Any] | None
    ) -> Completion:
        body: dict[str, Any] = {
            "model": model,
            "temperature": 0,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if response_format is not None:
            body["response_format"] = response_format
        data = await self._post("/chat/completions", body)
        usage = data["usage"]
        return Completion(
            content=data["choices"][0]["message"]["content"],
            tokens_in=usage["prompt_tokens"],
            tokens_out=usage["completion_tokens"],
        )

    async def embed(self, model: str, text: str) -> Embedding:
        data = await self._post("/embeddings", {"model": model, "input": text})
        return Embedding(vector=data["data"][0]["embedding"], tokens=data["usage"]["prompt_tokens"])

    async def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        async with self._client_factory() as client:
            response = await client.post(path, json=body)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data


def http_client_factory(settings: Settings) -> ClientFactory:
    return lambda: httpx.AsyncClient(
        base_url=settings.LLM_API_BASE,
        headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
