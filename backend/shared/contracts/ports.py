from datetime import date
from typing import Protocol, runtime_checkable

from shared.contracts.schemas import (
    ClientProfile,
    CounterpartyContext,
    Factor,
    HouseViewClaim,
    InsightCard,
    InterpretRequest,
    InterpretResponse,
    NewsItem,
    PageContext,
    ProductOffer,
    Trace,
    WhatIfResult,
)


@runtime_checkable
class ProfileService(Protocol):
    async def get_profile(self, user_id: str, client_id: str) -> ClientProfile: ...
    async def list_clients(self, user_id: str) -> list[str]: ...
    async def apply_user_correction(
        self, user_id: str, client_id: str, feature: str, value: object
    ) -> ClientProfile: ...


@runtime_checkable
class CounterpartyService(Protocol):
    async def context(
        self, client_id: str, beneficiary_id: str | None, inn: str | None
    ) -> CounterpartyContext: ...


@runtime_checkable
class NewsService(Protocol):
    async def search(
        self,
        factors: list[str],
        industry: str | None,
        region: str | None,
        country: str | None,
        since: date,
        limit: int = 10,
    ) -> list[NewsItem]: ...
    async def annotate(self, title: str, text: str, url: str) -> NewsItem: ...


@runtime_checkable
class PageContextService(Protocol):
    async def classify(self, page: PageContext) -> tuple[str, list[str], list[Factor]]: ...


@runtime_checkable
class HouseViewService(Protocol):
    async def claims(self, subject: str, as_of: date) -> list[HouseViewClaim]: ...
    async def chain(self, claim_id: str) -> list[HouseViewClaim]: ...
    async def version(self) -> str: ...


@runtime_checkable
class WhatIfService(Protocol):
    async def rate_burden(
        self, portfolio_amount: float, rate_now: float, rate_expected: float, months: int
    ) -> WhatIfResult: ...
    async def deposit_terms(
        self, amount: float, term_days: int, rate_path: list[float]
    ) -> WhatIfResult: ...
    async def fx_exposure(
        self, amount: float, currency: str, rate_now: float, rate_forecast: float
    ) -> WhatIfResult: ...


@runtime_checkable
class ProductRulesService(Protocol):
    async def match(
        self, profile: ClientProfile, action_type: str, claims: list[str]
    ) -> ProductOffer | None: ...


@runtime_checkable
class LLMGateway(Protocol):
    async def complete(
        self, task: str, system: str, user: str, schema: type | None = None
    ) -> tuple[object, int, int]: ...
    async def embed(self, text: str) -> list[float]: ...
    async def budget_left_rub(self) -> float: ...


@runtime_checkable
class TraceStore(Protocol):
    async def save(self, trace: Trace) -> None: ...
    async def get(self, trace_id: str) -> Trace | None: ...
    async def metrics(self, since: date) -> dict[str, float]: ...
    async def feedback(
        self, user_id: str, card_id: str, useful: bool, comment: str | None
    ) -> None: ...
    async def find_by_card(self, user_id: str, client_id: str, card_id: str) -> Trace: ...


@runtime_checkable
class Critic(Protocol):
    async def review(
        self, card: InsightCard, house_view: list[HouseViewClaim], news: list[NewsItem]
    ) -> list[str]: ...


@runtime_checkable
class Interpreter(Protocol):
    async def interpret(self, request: InterpretRequest) -> InterpretResponse: ...
