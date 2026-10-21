# CONTRACTS

Контракты — единственный способ взаимодействия сервисов. Схемы — Pydantic v2 в `shared/contracts/schemas.py`, порты — `typing.Protocol` в `shared/contracts/ports.py`. Фронт получает те же схемы как JSON Schema из `shared/contracts/openapi/` и генерирует из них TypeScript-типы.

Изменение контракта — только задача типа contract, порядок шагов — в `docs/PIPELINE.md`.

## Схемы

```python
# shared/contracts/schemas.py — целевой вид, реализуется в задаче AH-3

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal
from pydantic import BaseModel, Field


class Role(StrEnum):
    OWNER = "owner"
    CEO = "ceo"
    CFO = "cfo"
    TREASURER = "treasurer"
    CHIEF_ACCOUNTANT = "chief_accountant"


class PaymentContext(BaseModel):
    type: Literal["payment"] = "payment"
    beneficiary_id: str | None = None
    inn: str | None = None
    amount: float
    currency: str = "RUB"


class DepositContext(BaseModel):
    type: Literal["deposit"] = "deposit"
    amount: float
    term_days: int


class FxContext(BaseModel):
    type: Literal["fx"] = "fx"
    currency: str
    country: str | None = None
    amount: float


class LoanContext(BaseModel):
    type: Literal["loan"] = "loan"
    product: Literal["loan", "leasing", "guarantee"]
    amount: float
    rate_type: Literal["floating", "fixed"] | None = None


class PayrollContext(BaseModel):
    type: Literal["payroll"] = "payroll"
    headcount: int | None = None
    amount: float


class DashboardContext(BaseModel):
    type: Literal["dashboard"] = "dashboard"


class PageContext(BaseModel):
    type: Literal["page"] = "page"
    url: str
    text: str
    entities: list[str] = Field(default_factory=list)


class FollowupContext(BaseModel):
    type: Literal["followup"] = "followup"
    card_id: str
    question: str


ActionContext = Annotated[
    PaymentContext | DepositContext | FxContext | LoanContext | PayrollContext
    | DashboardContext | PageContext | FollowupContext,
    Field(discriminator="type"),
]


class InterpretRequest(BaseModel):
    user_id: str
    client_id: str
    role: Role
    action_context: ActionContext


class ClaimType(StrEnum):
    FACT = "fact"
    BANK = "bank"
    AI = "ai"


class SourceRef(BaseModel):
    kind: Literal["news", "house_view", "profile", "graph", "calc"]
    id: str
    title: str | None = None
    url: str | None = None
    published_at: datetime | None = None


class Claim(BaseModel):
    text: str
    type: ClaimType
    source_ref: SourceRef


class ProductOffer(BaseModel):
    product: str
    reason: str
    rule_id: str


class InsightCard(BaseModel):
    id: str
    headline: str
    what_happened: list[Claim]
    why_for_you: list[Claim]
    consequences: list[Claim]
    actions: list[Claim]
    bank_view: list[Claim]
    basis: list[SourceRef]
    product_offer: ProductOffer | None = None
    significance: float = Field(ge=0, le=1)
    needs_review: bool = False
    trace_id: str


class InterpretResponse(BaseModel):
    silent: bool
    silent_reason: str | None = None
    cards: list[InsightCard] = Field(default_factory=list)
    cached: bool = False


class Feature(BaseModel):
    value: str | float | bool | list[str] | None
    source: Literal["bank", "graph", "inferred", "user"]
    confidence: float = Field(ge=0, le=1)
    updated_at: datetime


class ClientProfile(BaseModel):
    client_id: str
    group_id: str | None
    group_members: list[str]
    features: dict[str, Feature]
    exposures: dict[str, float]
    flags: dict[str, bool]
    version: int


class CounterpartyContext(BaseModel):
    industry_class: str | None
    region: str | None
    size_bucket: str | None
    share_of_client_outflow: float | None
    share_of_counterparty_inflow: float | None
    confidence: float


class Factor(BaseModel):
    name: str
    direction: Literal["up", "down", "neutral"]
    strength: float = Field(ge=0, le=1)
    horizon: Literal["week", "month", "quarter", "year"]


class NewsItem(BaseModel):
    id: str
    title: str
    text: str
    url: str
    published_at: datetime
    source: str
    entities: list[str]
    factors: list[Factor]


class HouseViewClaim(BaseModel):
    id: str
    claim: str
    type: Literal["fact", "forecast", "opinion"]
    subject: str
    value: str | None
    date: date
    valid_until: date | None
    source_doc: str
    page: int | None
    superseded_by: str | None
    status: Literal["draft", "approved", "superseded", "expired"]


class WhatIfResult(BaseModel):
    kind: str
    value: float
    unit: str
    formula: str
    assumptions: list[str]


class TraceStep(BaseModel):
    step: Literal["prefilter", "plan", "tool", "draft", "critic", "final"]
    name: str
    input_summary: str
    output_summary: str
    model: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0
    started_at: datetime


class Trace(BaseModel):
    id: str
    request: InterpretRequest
    steps: list[TraceStep]
    critic_verdicts: list[str]
    result: InterpretResponse | None
    created_at: datetime
```

## Порты

```python
# shared/contracts/ports.py — целевой вид

from datetime import date
from typing import Protocol

from shared.contracts.schemas import (
    ClientProfile, CounterpartyContext, Factor, HouseViewClaim, InsightCard,
    InterpretRequest, InterpretResponse, NewsItem, PageContext, ProductOffer,
    Trace, WhatIfResult,
)


class ProfileService(Protocol):
    async def get_profile(self, user_id: str, client_id: str) -> ClientProfile: ...
    async def list_clients(self, user_id: str) -> list[str]: ...
    async def apply_user_correction(self, user_id: str, client_id: str, feature: str, value: object) -> ClientProfile: ...


class CounterpartyService(Protocol):
    async def context(self, client_id: str, beneficiary_id: str | None, inn: str | None) -> CounterpartyContext: ...


class NewsService(Protocol):
    async def search(self, factors: list[str], industry: str | None, region: str | None,
                     country: str | None, since: date, limit: int = 10) -> list[NewsItem]: ...
    async def annotate(self, title: str, text: str, url: str) -> NewsItem: ...


class PageContextService(Protocol):
    async def classify(self, page: PageContext) -> tuple[str, list[str], list[Factor]]: ...


class HouseViewService(Protocol):
    async def claims(self, subject: str, as_of: date) -> list[HouseViewClaim]: ...
    async def chain(self, claim_id: str) -> list[HouseViewClaim]: ...
    async def version(self) -> str: ...


class WhatIfService(Protocol):
    async def rate_burden(self, portfolio_amount: float, rate_now: float, rate_expected: float, months: int) -> WhatIfResult: ...
    async def deposit_terms(self, amount: float, term_days: int, rate_path: list[float]) -> WhatIfResult: ...
    async def fx_exposure(self, amount: float, currency: str, rate_now: float, rate_forecast: float) -> WhatIfResult: ...


class ProductRulesService(Protocol):
    async def match(self, profile: ClientProfile, action_type: str, claims: list[str]) -> ProductOffer | None: ...


class LLMGateway(Protocol):
    async def complete(self, task: str, system: str, user: str, schema: type | None = None) -> tuple[object, int, int]: ...
    async def embed(self, text: str) -> list[float]: ...
    async def budget_left_rub(self) -> float: ...


class TraceStore(Protocol):
    async def save(self, trace: Trace) -> None: ...
    async def get(self, trace_id: str) -> Trace | None: ...
    async def metrics(self, since: date) -> dict[str, float]: ...


class Critic(Protocol):
    async def review(self, card: InsightCard, house_view: list[HouseViewClaim], news: list[NewsItem]) -> list[str]: ...


class Interpreter(Protocol):
    async def interpret(self, request: InterpretRequest) -> InterpretResponse: ...
```

`HouseViewService.version()` — версия подтверждённого house view: первые 16 символов sha256 от всех утверждений со статусом `approved` (все поля, по порядку `id`). Меняется при любой правке подтверждённого набора, не меняется при повторном `seed` и от черновиков; статусы `superseded`/`expired`, вычисляемые на дату, в неё не входят. Gateway кладёт её в ключ кэша карточки.

## HTTP (gateway)

| Метод | Путь | Тело / ответ |
|---|---|---|
| POST | `/interpret` | `InterpretRequest` → `InterpretResponse` |
| GET | `/profile/{client_id}` | `ClientProfile` |
| PATCH | `/profile/{client_id}/features/{name}` | `{value}` → `ClientProfile` |
| GET | `/clients` | `list[str]` для текущего пользователя |
| POST | `/feedback` | `{card_id, useful: bool, comment?}` |
| GET | `/trace/{trace_id}` | `Trace` |
| GET | `/metrics` | `dict[str, float]` |
| POST | `/auth/mock` | `{user_id}` → cookie сессии (только прототип) |
| POST | `/auth/extension-token` | → `{token, expires_at}` |

## Контрактные тесты

Соответствие порту (`isinstance`-проверка через `runtime_checkable`) — `tests/unit/<service>/test_contract.py` для каждой реализации. Round-trip схем и инварианты домена (у каждого Claim есть source_ref; CounterpartyContext не содержит чужих идентификаторов; `bank`-тезисы ссылаются на approved claims) — `tests/integration/contracts/`.
