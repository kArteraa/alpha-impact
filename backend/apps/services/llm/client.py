from dataclasses import dataclass
from typing import Any

import httpx

from apps.services.llm.errors import ModelUnavailable
from shared.config.settings import Settings


@dataclass(frozen=True)
class Completion:
    content: str | None
    tokens_in: int
    tokens_out: int


@dataclass(frozen=True)
class Embedding:
    vector: list[float]
    tokens: int


class ModelClient:
    def __init__(self, http: httpx.AsyncClient) -> None:
        self._http = http

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
        try:
            response = await self._http.post(path, json=body)
            response.raise_for_status()
        except httpx.HTTPError as error:
            raise ModelUnavailable(f"model API {path} failed: {error}") from error
        data: dict[str, Any] = response.json()
        return data


def build_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.LLM_API_BASE,
        headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
