from asyncio import gather
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from math import fsum, isfinite

from apps.services.interpreter.context import current_claims
from shared.config.factors import FACTORS
from shared.config.house_view_topics import topics_for
from shared.config.news_entities import COUNTRY, INDUSTRY, PRODUCT, REGION, entity
from shared.contracts.ports import HouseViewService, NewsService
from shared.contracts.schemas import (
    ActionContext,
    ClientProfile,
    CounterpartyContext,
    DepositContext,
    FxContext,
    HouseViewClaim,
    LoanContext,
    NewsItem,
    PaymentContext,
    PayrollContext,
)

EXACT_MATCH_WEIGHT = 1.0


@dataclass(frozen=True)
class Candidate:
    news: NewsItem
    score: float


@dataclass(frozen=True)
class PrefilterResult:
    candidates: list[Candidate]
    house_view: list[HouseViewClaim]


def feature_entities(profile: ClientProfile, name: str) -> set[str]:
    feature = profile.features.get(name)
    if feature is None:
        return set()
    if isinstance(feature.value, str):
        return {feature.value} if feature.value else set()
    if isinstance(feature.value, list):
        return {value for value in feature.value if value}
    return set()


def entity_dimensions(
    profile: ClientProfile, counterparty: CounterpartyContext | None, action: ActionContext
) -> tuple[set[str], set[str], set[str], set[str]]:
    if isinstance(action, PaymentContext):
        industry = (
            {counterparty.industry_class} if counterparty and counterparty.industry_class else set()
        )
        region = {counterparty.region} if counterparty and counterparty.region else set()
    else:
        industry = feature_entities(profile, "industry_class")
        region = feature_entities(profile, "region")
    countries = feature_entities(profile, "import_countries")
    if isinstance(action, FxContext) and action.country:
        countries.add(action.country)
    products = feature_entities(profile, "products")
    if isinstance(action, LoanContext):
        products.add(action.product)
    elif isinstance(action, DepositContext):
        products.add("deposit")
    elif isinstance(action, PayrollContext):
        products.add("payroll")
    return industry, region, countries, products


def news_topics(news: Sequence[NewsItem], subjects: Sequence[str]) -> set[str]:
    factors = {factor.name for item in news for factor in item.factors if factor.strength > 0}
    return topics_for(factors).union(subjects)


def news_claims(
    news: Sequence[NewsItem], claims: list[HouseViewClaim], subjects: Sequence[str]
) -> list[HouseViewClaim]:
    topics = news_topics(news, subjects)
    return [claim for claim in claims if claim.subject in topics]


def score_news(
    item: NewsItem,
    profile: ClientProfile,
    counterparty: CounterpartyContext | None,
    action: ActionContext,
) -> float:
    strengths: dict[str, float] = {}
    for factor in item.factors:
        if factor.name in FACTORS:
            strengths[factor.name] = max(strengths.get(factor.name, 0.0), factor.strength)
    dot_product = fsum(
        strength * profile.exposures[name]
        for name, strength in strengths.items()
        if name in profile.exposures
    )
    entities = set(item.entities)
    matches = sum(
        any(entity(kind, value) in entities for value in values)
        for kind, values in zip(
            (INDUSTRY, REGION, COUNTRY, PRODUCT),
            entity_dimensions(profile, counterparty, action),
            strict=True,
        )
    )
    return dot_product + EXACT_MATCH_WEIGHT * matches


class Prefilter:
    def __init__(
        self, news: NewsService, house_view: HouseViewService, *, threshold: float
    ) -> None:
        if not isfinite(threshold) or threshold <= 0:
            raise ValueError("Relevance threshold must be finite and positive")
        self._news = news
        self._house_view = house_view
        self._threshold = threshold

    async def select(
        self,
        profile: ClientProfile,
        action: ActionContext,
        counterparty: CounterpartyContext | None,
        *,
        since: date,
        as_of: date,
        limit: int,
        subjects: Sequence[str],
    ) -> PrefilterResult:
        if since > as_of:
            raise ValueError("since must not be after as_of")
        if limit <= 0:
            raise ValueError("Search limit must be positive")
        items = await self._news.search(
            factors=[], industry=None, region=None, country=None, since=since, limit=limit
        )
        recent = [item for item in items if since <= item.published_at.date() <= as_of]
        return await self.rank(
            recent, profile, action, counterparty, as_of=as_of, subjects=subjects
        )

    async def rank(
        self,
        items: list[NewsItem],
        profile: ClientProfile,
        action: ActionContext,
        counterparty: CounterpartyContext | None,
        *,
        as_of: date,
        subjects: Sequence[str],
    ) -> PrefilterResult:
        candidates = []
        for item in items:
            score = score_news(item, profile, counterparty, action)
            if score >= self._threshold:
                candidates.append(Candidate(news=item, score=score))
        candidates.sort(key=lambda candidate: (-candidate.score, candidate.news.id))
        topics = sorted(
            news_topics(
                [candidate.news for candidate in candidates], subjects if candidates else ()
            )
        )
        batches = await gather(
            *(self._house_view.claims(subject=subject, as_of=as_of) for subject in topics)
        )
        claims = {
            claim.id: claim
            for subject, batch in zip(topics, batches, strict=True)
            for claim in current_claims(batch, as_of)
            if claim.subject == subject
        }
        return PrefilterResult(
            candidates=candidates, house_view=[claims[key] for key in sorted(claims)]
        )
