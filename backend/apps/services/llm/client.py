import math
from dataclasses import dataclass
from typing import Any

import httpx

from apps.services.llm.errors import ModelUnavailable
from shared.config.settings import Settings

CHAT_PATH = "/chat/completions"
MALFORMED_RESPONSE = (ValueError, KeyError, IndexError, TypeError)


@dataclass(frozen=True)
class Completion:
    content: str | None
    tokens_in: int
    tokens_out: int
    cost_rub: float


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
        try:
            response = await self._http.post(CHAT_PATH, json=body)
            response.raise_for_status()
            data = response.json()
        except httpx.TimeoutException as error:
            message = f"model API {CHAT_PATH} timed out: {error!r}"
            raise ModelUnavailable(message, cost_rub=None) from error
        except (httpx.HTTPError, ValueError) as error:
            raise ModelUnavailable(f"model API {CHAT_PATH} failed: {error!r}") from error
        try:
            return read_completion(data)
        except MALFORMED_RESPONSE as error:
            message = f"model API {CHAT_PATH} returned a malformed body: {error!r}"
            raise ModelUnavailable(message, *read_usage(data)) from error


def token_count(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise TypeError(f"token count must be a non-negative integer, got {value!r}")
    return value


def text_content(value: Any) -> str | None:
    if value is not None and not isinstance(value, str):
        raise TypeError(f"message content must be a string, got {type(value).__name__}")
    return value


def cost_value(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise TypeError(f"cost must be a number, got {value!r}")
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"cost must be a finite non-negative number, got {value!r}")
    return float(value)


def counted_or_zero(usage: dict[str, Any], field: str) -> int:
    try:
        return token_count(usage[field])
    except MALFORMED_RESPONSE:
        return 0


def read_completion(data: Any) -> Completion:
    usage = data["usage"]
    return Completion(
        content=text_content(data["choices"][0]["message"]["content"]),
        tokens_in=token_count(usage["prompt_tokens"]),
        tokens_out=token_count(usage["completion_tokens"]),
        cost_rub=cost_value(usage["cost"]),
    )


def read_usage(data: Any) -> tuple[int, int, float | None]:
    usage = data.get("usage") if isinstance(data, dict) else None
    if not isinstance(usage, dict):
        return 0, 0, 0.0
    try:
        cost = cost_value(usage["cost"])
    except MALFORMED_RESPONSE:
        return 0, 0, None
    tokens_in = counted_or_zero(usage, "prompt_tokens")
    return tokens_in, counted_or_zero(usage, "completion_tokens"), cost


def build_http_client(settings: Settings) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=settings.LLM_API_BASE,
        headers={"Authorization": f"Bearer {settings.LLM_API_KEY}"},
        timeout=settings.LLM_TIMEOUT_SECONDS,
    )
