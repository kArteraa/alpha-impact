import math
from datetime import UTC, datetime
from email.utils import format_datetime
from typing import Any

from pydantic import BaseModel

from shared.config.embedding import EMBEDDING_DIMENSION
from shared.contracts.errors import DomainError

NOW = datetime(2026, 10, 21, 12, 0, tzinfo=UTC)
TOKENS_IN = 100
TOKENS_OUT = 20
EMPTY_ANSWER: dict[str, Any] = {
    "factors": [],
    "industries": [],
    "regions": [],
    "countries": [],
    "companies": [],
}
KEY_RATE_ANSWER: dict[str, Any] = {
    "factors": [{"name": "key_rate", "direction": "down", "strength": 0.8, "horizon": "quarter"}],
    "industries": ["finance"],
    "regions": ["Москва"],
    "countries": ["Китай"],
    "companies": ["Сбербанк"],
}


def item(title: str, link: str, published: datetime, description: str | None = None) -> str:
    text = "" if description is None else f"<description>{description}</description>"
    return (
        f"<item><title>{title}</title><link>{link}</link>{text}"
        f"<pubDate>{format_datetime(published)}</pubDate></item>"
    )


def rss(*items: str) -> bytes:
    body = "".join(items)
    return (
        '<?xml version="1.0" encoding="utf-8"?>'
        f'<rss version="2.0"><channel><title>Лента</title>{body}</channel></rss>'
    ).encode()


def unit(index: int) -> list[float]:
    return [1.0 if position == index else 0.0 for position in range(EMBEDDING_DIMENSION)]


def near(index: int, other: int) -> list[float]:
    raw = [a * 0.99 + b * 0.1 for a, b in zip(unit(index), unit(other), strict=True)]
    norm = math.sqrt(sum(value * value for value in raw))
    return [value / norm for value in raw]


class FakeNewsLlm:
    def __init__(
        self,
        vectors: dict[str, list[float]] | None = None,
        answers: dict[str, dict[str, Any]] | None = None,
        errors: dict[str, DomainError] | None = None,
        embed_errors: dict[str, DomainError] | None = None,
    ) -> None:
        self.vectors = vectors or {}
        self.answers = answers or {}
        self.errors = errors or {}
        self.embed_errors = embed_errors or {}
        self.completions: list[str] = []
        self.embedded: list[str] = []
        self.tasks: list[str] = []
        self._fresh: dict[str, int] = {}

    async def complete(
        self, task: str, system: str, user: str, schema: type | None = None
    ) -> tuple[object, int, int]:
        assert schema is not None and issubclass(schema, BaseModel)
        self.tasks.append(task)
        self.completions.append(user)
        failing = next((title for title in self.errors if title in user), None)
        if failing is not None:
            raise self.errors.pop(failing)
        answer = next((value for key, value in self.answers.items() if key in user), EMPTY_ANSWER)
        return schema.model_validate(answer), TOKENS_IN, TOKENS_OUT

    async def embed(self, text: str) -> list[float]:
        self.embedded.append(text)
        failing = next((key for key in self.embed_errors if key in text), None)
        if failing is not None:
            raise self.embed_errors.pop(failing)
        vector = next((value for key, value in self.vectors.items() if key in text), None)
        if vector is not None:
            return vector
        index = self._fresh.setdefault(text, EMBEDDING_DIMENSION - 1 - len(self._fresh))
        return unit(index)

    async def budget_left_rub(self) -> float:
        return 100.0
