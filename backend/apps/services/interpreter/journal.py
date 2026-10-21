import json
from collections.abc import Awaitable
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

    async def tool[T](self, name: str, summary: str, operation: Awaitable[T]) -> T:
        step = TraceStep(
            step="tool", name=name, input_summary=summary, output_summary="", started_at=utc_now()
        )
        start = perf_counter()
        try:
            result = await operation
            step.output_summary = (
                f"{len(result)} items" if isinstance(result, list) else type(result).__name__
            )
            return result
        except Exception as error:
            step.output_summary = type(error).__name__
            raise
        finally:
            step.duration_ms = int((perf_counter() - start) * 1000)
            self.trace.steps.append(step)

    async def generate[T: BaseModel](self, name: str, system: str, user: str, schema: type[T]) -> T:
        step = TraceStep(
            step="plan" if name == "plan" else "draft",
            name=name,
            input_summary=f"{len(user)} characters of structured context",
            output_summary="",
            model=self.model,
            started_at=utc_now(),
        )
        start = perf_counter()
        try:
            raw, step.tokens_in, step.tokens_out = await self.llm.complete(
                task="interpret", system=system, user=user, schema=schema
            )
            result = schema.model_validate(raw)
            step.output_summary = result.model_dump_json() if name == "plan" else "draft received"
            return result
        except Exception as error:
            step.output_summary = type(error).__name__
            raise
        finally:
            step.duration_ms = int((perf_counter() - start) * 1000)
            self.trace.steps.append(step)

    async def review(
        self,
        round_number: int,
        critic: Critic,
        card: InsightCard,
        house_view: list[HouseViewClaim],
        news: list[NewsItem],
    ) -> list[str]:
        step = TraceStep(
            step="critic",
            name=f"round {round_number}",
            input_summary=f"card {card.id}, {len(card.basis)} sources",
            output_summary="",
            started_at=utc_now(),
        )
        start = perf_counter()
        try:
            verdicts = await critic.review(card, house_view, news)
            step.output_summary = json.dumps(verdicts, ensure_ascii=False)
            self.trace.critic_verdicts.extend(
                [f"{round_number}: {verdict}" for verdict in verdicts] or [f"{round_number}: ok"]
            )
            return verdicts
        except Exception as error:
            step.output_summary = type(error).__name__
            raise
        finally:
            step.duration_ms = int((perf_counter() - start) * 1000)
            self.trace.steps.append(step)
