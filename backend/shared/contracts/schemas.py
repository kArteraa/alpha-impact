import datetime as dt
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
    PaymentContext
    | DepositContext
    | FxContext
    | LoanContext
    | PayrollContext
    | DashboardContext
    | PageContext
    | FollowupContext,
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
    published_at: dt.datetime | None = None


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
    updated_at: dt.datetime


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
    published_at: dt.datetime
    source: str
    entities: list[str]
    factors: list[Factor]


class HouseViewClaim(BaseModel):
    id: str
    claim: str
    type: Literal["fact", "forecast", "opinion"]
    subject: str
    value: str | None
    date: dt.date
    valid_until: dt.date | None
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
    started_at: dt.datetime


class Trace(BaseModel):
    id: str
    request: InterpretRequest
    steps: list[TraceStep]
    critic_verdicts: list[str]
    result: InterpretResponse | None
    created_at: dt.datetime
