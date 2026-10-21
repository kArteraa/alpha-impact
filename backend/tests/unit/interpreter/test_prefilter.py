from unittest.mock import AsyncMock

import pytest

from apps.services.interpreter.prefilter import Prefilter, score_news
from scripts.prefilter_mocks import MockSeed, make_seed
from shared.contracts.ports import HouseViewService, NewsService
from shared.contracts.schemas import (
    DashboardContext,
    DepositContext,
    Factor,
    Feature,
    FxContext,
    LoanContext,
    PaymentContext,
)


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
        (["logistics"], 1.1),
        (["Москва"], 1.1),
        (["CN"], 1.1),
        (["settlement"], 1.1),
        (["logistics", "Москва", "CN", "settlement"], 4.1),
        (["logistics", "logistics"], 1.1),
        (["transport_logistics", "CN-extra", "settlement_extra"], 0.1),
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
    item = seed.news[0].model_copy(update={"entities": [product], "factors": []})
    assert score_news(item, seed.profile, None, action) == 1.0


def test_fx_country_is_an_exact_match_without_profile_feature(seed: MockSeed) -> None:
    profile = seed.profile.model_copy(update={"features": {}})
    item = seed.news[0].model_copy(update={"entities": ["IN"], "factors": []})
    assert score_news(item, profile, None, FxContext(amount=1, currency="INR", country="IN")) == 1.0


def test_absent_features_and_exposures_are_not_evidence(seed: MockSeed) -> None:
    profile = seed.profile.model_copy(update={"features": {}, "exposures": {}})
    assert score_news(seed.news[0], profile, None, PaymentContext(amount=1)) == 0.0


def test_dashboard_uses_client_industry_and_region(seed: MockSeed) -> None:
    item = seed.news[0].model_copy(update={"entities": ["it", "Санкт-Петербург"], "factors": []})
    assert score_news(item, seed.profile, None, DashboardContext()) == 2.0


def test_multiple_values_in_one_dimension_add_only_one(seed: MockSeed) -> None:
    feature = seed.profile.features["import_countries"].model_copy(update={"value": ["CN", "IN"]})
    profile = seed.profile.model_copy(
        update={"features": {**seed.profile.features, "import_countries": feature}}
    )
    item = seed.news[0].model_copy(update={"entities": ["CN", "IN"], "factors": []})
    assert score_news(item, profile, None, seed.payment) == 1.0


@pytest.mark.parametrize("threshold", [-1.0, 0.0, float("nan"), float("inf")])
def test_invalid_threshold_is_rejected(threshold: float) -> None:
    with pytest.raises(ValueError, match="threshold"):
        Prefilter(
            AsyncMock(spec=NewsService), AsyncMock(spec=HouseViewService), threshold=threshold
        )
