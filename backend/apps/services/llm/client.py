from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import httpx

from apps.services.llm.errors import ModelUnavailable
from shared.config.settings import Settings

MALFORMED_RESPONSE = (ValueError, KeyError, IndexError, TypeError)


@dataclass(frozen=True)
class Completion:
    content: str | None
    tokens_in: int
    tokens_out: int


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
        return await self._call("/chat/completions", body, read_completion)

    async def _call[T](self, path: str, body: dict[str, Any], read: Callable[[Any], T]) -> T:
        try:
            response = await self._http.post(path, json=body)
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as error:
            raise ModelUnavailable(f"model API {path} failed: {error!r}") from error
        try:
            return read(data)
        except MALFORMED_RESPONSE as error:
            tokens_in, tokens_out = read_usage(data)
            message = f"model API {path} returned a malformed body: {error!r}"
            raise ModelUnavailable(message, tokens_in, tokens_out) from error


def token_count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TypeError(f"token count must be a non-negative integer, got {value!r}")
    return value


def text_content(value: Any) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"message content must be a string, got {type(value).__name__}")
    return value


def read_completion(data: Any) -> Completion:
    usage = data["usage"]
    return Completion(
        content=text_content(data["choices"][0]["message"]["content"]),
        tokens_in=token_count(usage["prompt_tokens"]),
        tokens_out=token_count(usage["completion_tokens"]),
    )


def read_usage(data: Any) -> tuple[int, int]:
    try:
        usage = data["usage"]
        return token_count(usage["prompt_tokens"]), token_count(usage.get("completion_tokens", 0))
    except MALFORMED_RESPONSE:
        return 0, 0


def build_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.LLM_API_BASE,
        headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
