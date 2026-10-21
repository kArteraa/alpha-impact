import pytest

from apps.services.profile.builder import FEATURES, Payload, build_profiles
from apps.services.profile.config import load_config
from apps.services.profile.loader import load_companies
from tests.unit.profile.fixtures import COMPANIES_CSV

FACTORS = (
    "key_rate",
    "fx_rate",
    "trade_logistics",
    "commodity_prices",
    "construction_demand",
    "consumer_demand",
    "labor_market",
    "regulation",
)

CHECKED_EXPOSURES = {
    "U_1595": (0.7, 0.9, 0.4, 0.0, 0.0, 0.7, 0.9, 0.3),
    "U_1941": (0.7, 0.8, 0.7, 0.0, 0.0, 0.0, 0.9, 0.0),
    "U_3263": (0.3, 0.6, 1.0, 0.0, 0.0, 0.0, 0.9, 0.0),
    "U_4909": (0.0, 0.0, 0.0, 0.6, 0.0, 0.0, 0.9, 0.4),
    "U_4217": (0.7, 0.0, 0.0, 0.0, 0.0, 0.0, 0.9, 0.5),
    "U_3642": (0.2, 0.0, 0.0, 0.0, 0.6, 0.0, 0.2, 0.0),
    "U_3708": (0.4, 0.0, 0.3, 0.8, 0.0, 0.0, 0.4, 0.0),
    "U_9250": (1.0, 0.6, 0.4, 0.0, 0.8, 0.0, 0.9, 0.0),
    "U_12750": (0.7, 0.8, 0.6, 0.6, 0.0, 0.0, 0.4, 0.0),
    "U_44245": (0.3, 0.6, 0.6, 0.0, 0.0, 0.7, 0.9, 0.0),
}


@pytest.fixture(scope="module")
def profiles() -> dict[str, Payload]:
    config = load_config()
    return build_profiles(load_companies(COMPANIES_CSV, config), config, frozenset())


def test_only_large_companies_and_placeholders_get_profiles(
    profiles: dict[str, Payload],
) -> None:
    assert set(profiles) == set(CHECKED_EXPOSURES) | {"U_428697"}


def test_linked_small_company_gets_profile() -> None:
    config = load_config()
    companies = load_companies(COMPANIES_CSV, config)
    profiles = build_profiles(companies, config, frozenset({"U_85511"}))

    assert set(profiles) == set(CHECKED_EXPOSURES) | {"U_428697", "U_85511"}
    assert profiles["U_85511"]["features"]["industry_class"]["value"] == "construction"


@pytest.mark.parametrize("client_id", sorted(CHECKED_EXPOSURES))
def test_exposures_match_hand_checked_values(profiles: dict[str, Payload], client_id: str) -> None:
    expected = dict(zip(FACTORS, CHECKED_EXPOSURES[client_id], strict=True))
    assert profiles[client_id]["exposures"] == expected


def test_features_carry_source_and_confidence(profiles: dict[str, Payload]) -> None:
    features = profiles["U_44245"]["features"]
    assert set(features) == set(FEATURES)
    assert features["okved_code"] == {"value": "45.11.2", "source": "bank", "confidence": 0.9}
    assert features["industry_class"] == {
        "value": "auto_dealer",
        "source": "inferred",
        "confidence": 0.7,
    }
    assert features["import_countries"] == {
        "value": ["ПОЛЬША"],
        "source": "bank",
        "confidence": 0.9,
    }
    assert features["products"]["value"] == ["settlement", "leasing", "payroll"]


def test_flags_describe_the_company(profiles: dict[str, Payload]) -> None:
    assert profiles["U_1941"]["flags"] == {
        "placeholder": False,
        "no_card": False,
        "imports": True,
        "negative_mark": True,
        "foreign_owned": False,
    }


def test_group_members_are_other_companies_of_the_group(
    profiles: dict[str, Payload],
) -> None:
    assert profiles["U_9250"]["group_id"] == "group_133188_sb"
    assert profiles["U_9250"]["group_members"] == ["U_116481", "U_85511"]
    assert profiles["U_1941"]["group_members"] == []


def test_placeholder_has_no_features_and_no_group(
    profiles: dict[str, Payload],
) -> None:
    placeholder = profiles["U_428697"]
    assert placeholder["features"] == {}
    assert placeholder["exposures"] == {}
    assert placeholder["group_id"] is None
    assert placeholder["group_members"] == []
    assert placeholder["flags"] == {
        "placeholder": True,
        "no_card": False,
        "imports": False,
        "negative_mark": False,
        "foreign_owned": False,
    }
    for profile in profiles.values():
        assert "U_428697" not in profile["group_members"]


def test_foreign_ownership_is_flagged(profiles: dict[str, Payload]) -> None:
    assert profiles["U_1595"]["flags"]["foreign_owned"] is True
    assert profiles["U_1595"]["features"]["ownership"]["value"] == (
        "СОБСТВЕННОСТЬ ИНОСТРАННЫХ ЮРИДИЧЕСКИХ ЛИЦ"
    )


def test_config_must_cover_shared_factors() -> None:
    config = load_config()
    missing = {name: rule for name, rule in config.exposures.items() if name != "regulation"}

    with pytest.raises(ValueError, match="shared factors"):
        type(config).model_validate({**config.model_dump(), "exposures": missing})
    reordered = dict(reversed(list(config.exposures.items())))
    assert type(config).model_validate({**config.model_dump(), "exposures": reordered})
