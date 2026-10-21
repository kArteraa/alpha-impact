from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from unittest.mock import AsyncMock

from pydantic import BaseModel

from apps.services import interpreter
from scripts.prefilter_mocks import MockSeed, make_seed
from shared.config.settings import Settings
from shared.contracts.ports import (
    CounterpartyService,
    HouseViewService,
    Interpreter,
    LLMGateway,
    NewsService,
    ProfileService,
    TraceStore,
)
from shared.contracts.schemas import InterpretRequest, Role
from shared.di.container import Container


def constant(value: object) -> Callable[[Container], object]:
    def factory(_: Container) -> object:
        return value

    return factory


def plan_answer() -> dict[str, object]:
    return {"focus": "Риск сроков доставки для платежа", "tools": []}


def draft_answer() -> dict[str, object]:
    return {
        "headline": "Проверьте сроки доставки до оплаты перевозчику",
        "what_happened": [
            {"text": "Стоимость перевозок растёт", "type": "fact", "source": "news:logistics-news"}
        ],
        "why_for_you": [
            {
                "text": "Получатель работает в логистике",
                "type": "fact",
                "source": "graph:industry_class",
            }
        ],
        "consequences": [
            {"text": "Возможен пересмотр тарифа", "type": "ai", "source": "news:logistics-news"}
        ],
        "actions": [
            {"text": "Уточните срок поставки", "type": "ai", "source": "graph:industry_class"}
        ],
        "bank_view": [
            {
                "text": make_seed().house_view[0].claim,
                "type": "bank",
                "source": "house_view:logistics-approved",
            }
        ],
        "significance": 0.8,
    }


@dataclass
class Harness:
    container: Container
    seed: MockSeed
    profiles: AsyncMock
    counterparties: AsyncMock
    news: AsyncMock
    house_view: AsyncMock
    llm: AsyncMock
    traces: AsyncMock
    answers: list[dict[str, object]]

    def request(self, beneficiary: str = "logistics") -> InterpretRequest:
        return InterpretRequest(
            user_id="private-user",
            client_id="private-client",
            role=Role.CFO,
            action_context=self.seed.payment.model_copy(update={"beneficiary_id": beneficiary}),
        )

    @property
    def agent(self) -> Interpreter:
        return self.container.resolve(Interpreter)


def make_harness(settings: Settings) -> Harness:
    seed = make_seed()
    now = datetime.now(UTC)
    seed.news = [item.model_copy(update={"published_at": now}) for item in seed.news]
    seed.house_view = [item.model_copy(update={"date": now.date()}) for item in seed.house_view]
    profiles = AsyncMock(spec=ProfileService)
    profiles.get_profile.return_value = seed.profile.model_copy(
        update={
            "client_id": "private-client",
            "group_id": "private-group",
            "group_members": ["secret"],
        }
    )
    counterparties = AsyncMock(spec=CounterpartyService)
    counterparties.context.side_effect = lambda client_id, beneficiary_id, inn: seed.counterparties[
        beneficiary_id or "logistics"
    ]
    news = AsyncMock(spec=NewsService)
    news.search.return_value = seed.news
    house_view = AsyncMock(spec=HouseViewService)
    house_view.claims.return_value = seed.house_view
    house_view.chain.return_value = seed.house_view
    llm = AsyncMock(spec=LLMGateway)
    traces = AsyncMock(spec=TraceStore)
    answers = [plan_answer(), draft_answer()]

    async def complete(
        task: str, system: str, user: str, schema: type[BaseModel]
    ) -> tuple[BaseModel, int, int]:
        return schema.model_validate(answers.pop(0)), 120, 40

    llm.complete.side_effect = complete
    container = Container()
    for port, service in (
        (ProfileService, profiles),
        (CounterpartyService, counterparties),
        (NewsService, news),
        (HouseViewService, house_view),
        (LLMGateway, llm),
        (TraceStore, traces),
        (Settings, settings),
    ):
        container.register(port, constant(service))
    interpreter.register(container)
    return Harness(
        container, seed, profiles, counterparties, news, house_view, llm, traces, answers
    )
