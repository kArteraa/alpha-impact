import json
from collections.abc import AsyncIterator, Awaitable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from time import perf_counter

from pydantic import BaseModel

from shared.contracts.ports import Critic, LLMGateway
from shared.contracts.schemas import HouseViewClaim, InsightCard, NewsItem, Trace, TraceStep


def utc_now() -> datetime:
    return datetime.now(UTC)


class Journal:
    def __init__(self, trace: Trace, llm: LLMGateway, model: str) -> None:
        self.trace = trace
        self.llm = llm
        self.model = model

    @asynccontextmanager
    async def _step(self, step: TraceStep) -> AsyncIterator[TraceStep]:
        start = perf_counter()
        try:
            yield step
        except Exception as error:
            step.output_summary = type(error).__name__
            raise
        finally:
            step.duration_ms = int((perf_counter() - start) * 1000)
            self.trace.steps.append(step)

    async def tool[T](self, name: str, summary: str, operation: Awaitable[T]) -> T:
        async with self._step(
            TraceStep(
                step="tool",
                name=name,
                input_summary=summary,
                output_summary="",
                started_at=utc_now(),
            )
        ) as step:
            result = await operation
            step.output_summary = (
                f"{len(result)} items" if isinstance(result, list) else type(result).__name__
            )
            return result

    async def generate[T: BaseModel](self, name: str, system: str, user: str, schema: type[T]) -> T:
        async with self._step(
            TraceStep(
                step="plan" if name == "plan" else "draft",
                name=name,
                input_summary=f"{len(user)} characters of structured context",
                output_summary="",
                model=self.model,
                started_at=utc_now(),
            )
        ) as step:
            raw, step.tokens_in, step.tokens_out = await self.llm.complete(
                task="interpret", system=system, user=user, schema=schema
            )
            result = schema.model_validate(raw)
            step.output_summary = result.model_dump_json() if name == "plan" else "draft received"
            return result

    async def review(
        self,
        round_number: int,
        critic: Critic,
        card: InsightCard,
        house_view: list[HouseViewClaim],
        news: list[NewsItem],
    ) -> list[str]:
        async with self._step(
            TraceStep(
                step="critic",
                name=f"round {round_number}",
                input_summary=f"card {card.id}, {len(card.basis)} sources",
                output_summary="",
                started_at=utc_now(),
            )
        ) as step:
            verdicts = await critic.review(card, house_view, news)
            step.output_summary = json.dumps(verdicts, ensure_ascii=False)
            self.trace.critic_verdicts.extend(
                [f"{round_number}: {verdict}" for verdict in verdicts] or [f"{round_number}: ok"]
            )
            return verdicts
