from unittest.mock import AsyncMock

import pytest

from apps.services.interpreter.prefilter import Prefilter, score_news
from apps.services.news.annotation import annotation_schema, to_news_item
from apps.services.news.config import load_config
from apps.services.news.feed import FeedEntry
from scripts.prefilter_mocks import MockSeed, make_seed
from shared.contracts.ports import HouseViewService, NewsService
from shared.contracts.schemas import (
    ClientProfile,
    DashboardContext,
    DepositContext,
    Factor,
    Feature,
    FxContext,
    LoanContext,
    NewsItem,
    PaymentContext,
)
from tests.news_data import EMPTY_ANSWER


@pytest.fixture
def seed() -> MockSeed:
    return make_seed()


def test_scalar_product_uses_all_shared_factors(seed: MockSeed) -> None:
    profile = seed.profile.model_copy(
        update={"exposures": {"trade_logistics": 0.4, "key_rate": 0.5}}
    )
    item = seed.news[0].model_copy(
        update={
            "entities": [],
            "factors": [
                Factor(name="trade_logistics", direction="down", strength=0.5, horizon="month"),
                Factor(name="key_rate", direction="up", strength=0.8, horizon="quarter"),
            ],
        }
    )
    assert score_news(
        item, profile, seed.counterparties["stationery"], seed.payment
    ) == pytest.approx(0.6)


@pytest.mark.parametrize("direction", ["up", "down", "neutral"])
def test_direction_does_not_cancel_exposure(seed: MockSeed, direction: str) -> None:
    factor = seed.news[0].factors[0].model_copy(update={"direction": direction})
    item = seed.news[0].model_copy(update={"entities": [], "factors": [factor]})
    assert score_news(item, seed.profile, None, seed.payment) == pytest.approx(0.1)


def test_duplicate_and_unknown_factors_do_not_inflate_score(seed: MockSeed) -> None:
    factor = seed.news[0].factors[0]
    item = seed.news[0].model_copy(
        update={
            "entities": [],
            "factors": [
                factor,
                factor.model_copy(update={"strength": 0.5}),
                factor.model_copy(update={"name": "unknown"}),
            ],
        }
    )
    profile = seed.profile.model_copy(
        update={"exposures": {"trade_logistics": 0.1, "unknown": 1.0}}
    )
    assert score_news(item, profile, None, seed.payment) == pytest.approx(0.1)


@pytest.mark.parametrize(
    ("entities", "expected"),
    [
        (["industry:logistics"], 1.1),
        (["region:москва"], 1.1),
        (["country:cn"], 1.1),
        (["product:settlement"], 1.1),
        (["industry:logistics", "region:москва", "country:cn", "product:settlement"], 4.1),
        (["industry:logistics", "industry:logistics"], 1.1),
        (["industry:transport_logistics", "country:cn-extra", "product:settlement_extra"], 0.1),
        (["logistics", "Москва", "КИТАЙ", "settlement"], 0.1),
        (["company:logistics", "industry:settlement"], 0.1),
        ([], 0.1),
    ],
)
def test_exact_entity_matches_add_one_per_dimension(
    seed: MockSeed, entities: list[str], expected: float
) -> None:
    item = seed.news[0].model_copy(update={"entities": entities})
    assert score_news(item, seed.profile, seed.counterparties["logistics"], seed.payment) == (
        pytest.approx(expected)
    )


def test_payment_uses_counterparty_instead_of_client_industry(seed: MockSeed) -> None:
    feature = Feature(
        value="logistics", source="user", confidence=1.0, updated_at=seed.news[0].published_at
    )
    profile = seed.profile.model_copy(update={"features": {"industry_class": feature}})
    assert score_news(seed.news[0], profile, seed.counterparties["stationery"], seed.payment) == 0.1
    assert score_news(seed.news[0], profile, None, seed.payment) == 0.1


@pytest.mark.parametrize(
    "action", [DepositContext(amount=1, term_days=30), LoanContext(amount=1, product="leasing")]
)
def test_operation_product_is_an_exact_match(
    seed: MockSeed, action: DepositContext | LoanContext
) -> None:
    product = "deposit" if isinstance(action, DepositContext) else action.product
    item = seed.news[0].model_copy(update={"entities": [f"product:{product}"], "factors": []})
    assert score_news(item, seed.profile, None, action) == 1.0


def test_fx_country_is_an_exact_match_without_profile_feature(seed: MockSeed) -> None:
    profile = seed.profile.model_copy(update={"features": {}})
    item = seed.news[0].model_copy(update={"entities": ["country:in"], "factors": []})
    assert score_news(item, profile, None, FxContext(amount=1, currency="INR", country="IN")) == 1.0


def test_absent_features_and_exposures_are_not_evidence(seed: MockSeed) -> None:
    profile = seed.profile.model_copy(update={"features": {}, "exposures": {}})
    assert score_news(seed.news[0], profile, None, PaymentContext(amount=1)) == 0.0


def test_dashboard_uses_client_industry_and_region(seed: MockSeed) -> None:
    item = seed.news[0].model_copy(
        update={"entities": ["industry:it", "region:санкт-петербург"], "factors": []}
    )
    assert score_news(item, seed.profile, None, DashboardContext()) == 2.0


def test_multiple_values_in_one_dimension_add_only_one(seed: MockSeed) -> None:
    feature = seed.profile.features["import_countries"].model_copy(
        update={"value": ["КИТАЙ", "ИНДИЯ"]}
    )
    profile = seed.profile.model_copy(
        update={"features": {**seed.profile.features, "import_countries": feature}}
    )
    item = seed.news[0].model_copy(update={"entities": ["country:cn", "country:in"], "factors": []})
    assert score_news(item, profile, None, seed.payment) == 1.0


def annotated(seed: MockSeed, **answer: list[str]) -> NewsItem:
    annotation = annotation_schema(load_config()).model_validate({**EMPTY_ANSWER, **answer})
    entry = FeedEntry("Новость", "", "https://a.example/1", seed.news[0].published_at, "a.example")
    return to_news_item(entry, annotation)


def with_feature(seed: MockSeed, name: str, value: object) -> ClientProfile:
    feature = seed.profile.features[name].model_copy(update={"value": value})
    return seed.profile.model_copy(update={"features": {name: feature}})


def test_profile_country_as_in_csv_matches_country_annotated_in_news(seed: MockSeed) -> None:
    item = annotated(seed, countries=["Объединённые Арабские Эмираты"])
    profile = with_feature(seed, "import_countries", ["ОАЭ"])

    assert score_news(item, profile, None, seed.payment) == 1.0


def test_profile_region_as_in_csv_matches_region_annotated_in_news(seed: MockSeed) -> None:
    item = annotated(seed, regions=["Бурятия"])
    profile = with_feature(seed, "region", "Бурятия (Республика)")

    assert score_news(item, profile, None, DashboardContext()) == 1.0


@pytest.mark.parametrize("threshold", [-1.0, 0.0, float("nan"), float("inf")])
def test_invalid_threshold_is_rejected(threshold: float) -> None:
    with pytest.raises(ValueError, match="threshold"):
        Prefilter(
            AsyncMock(spec=NewsService), AsyncMock(spec=HouseViewService), threshold=threshold
        )


def assessor(seed: MockSeed, threshold: float) -> tuple[Prefilter, AsyncMock, AsyncMock]:
    news = AsyncMock(spec=NewsService)
    house_view = AsyncMock(spec=HouseViewService)
    house_view.claims.return_value = seed.house_view
    return Prefilter(news, house_view, threshold=threshold), news, house_view


async def test_assess_keeps_relevant_item_with_current_house_view(seed: MockSeed) -> None:
    prefilter, news, house_view = assessor(seed, threshold=1.0)
    item = seed.news[0].model_copy(update={"entities": ["product:settlement"]})
    result = await prefilter.assess(item, seed.profile, DashboardContext(), as_of=seed.as_of)
    assert [candidate.news for candidate in result.candidates] == [item]
    assert result.candidates[0].score == pytest.approx(1.1)
    assert [claim.id for claim in result.house_view] == ["logistics-approved"]
    house_view.claims.assert_awaited_once_with(subject="trade_logistics", as_of=seed.as_of)
    news.search.assert_not_awaited()


async def test_assess_below_threshold_is_empty_without_house_view(seed: MockSeed) -> None:
    prefilter, _, house_view = assessor(seed, threshold=1.0)
    item = seed.news[0].model_copy(update={"entities": []})
    result = await prefilter.assess(item, seed.profile, DashboardContext(), as_of=seed.as_of)
    assert result.candidates == []
    assert result.house_view == []
    house_view.claims.assert_not_awaited()


async def test_assess_ignores_publication_window(seed: MockSeed) -> None:
    prefilter, _, _ = assessor(seed, threshold=0.1)
    item = seed.news[0].model_copy(
        update={"published_at": seed.news[0].published_at.replace(year=2020)}
    )
    result = await prefilter.assess(item, seed.profile, DashboardContext(), as_of=seed.as_of)
    assert len(result.candidates) == 1
