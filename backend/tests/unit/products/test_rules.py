import pytest

from apps.services.products.catalog import RULES_PATH, load_catalog
from apps.services.products.service import ProductCatalog
from tests.unit.products.profiles import make_profile

ALL_FLAGS = {"imports": True, "buyer_concentration": True, "free_balances": True}
ALL_CLAIMS = ["ruble_weakening", "industry_stress", "counterparty_industry_stress", "high_rate"]


@pytest.fixture
def catalog() -> ProductCatalog:
    return ProductCatalog(load_catalog(RULES_PATH))


@pytest.mark.parametrize(
    ("flags", "action_type", "claims", "rule_id"),
    [
        ({"imports": True}, "fx", ["ruble_weakening"], "fx_hedge"),
        ({"buyer_concentration": True}, "payroll", ["industry_stress"], "factoring"),
        ({"free_balances": True}, "deposit", ["high_rate"], "deposit"),
        ({}, "payment", ["counterparty_industry_stress"], "letter_of_credit"),
    ],
)
async def test_each_rule_offers_its_product(
    catalog: ProductCatalog,
    flags: dict[str, bool],
    action_type: str,
    claims: list[str],
    rule_id: str,
) -> None:
    offer = await catalog.match(make_profile(flags), action_type, claims)

    assert offer is not None
    assert offer.rule_id == rule_id
    assert offer.product
    assert offer.reason


@pytest.mark.parametrize(
    ("flags", "action_type", "claims"),
    [
        ({"imports": True}, "fx", []),
        ({"imports": False}, "fx", ["ruble_weakening"]),
        ({}, "fx", ["ruble_weakening"]),
        ({"buyer_concentration": True}, "payroll", ["ruble_weakening"]),
        ({"free_balances": True}, "loan", ["high_rate"]),
        ({}, "deposit", ["counterparty_industry_stress"]),
    ],
)
async def test_no_offer_when_conditions_are_not_met(
    catalog: ProductCatalog, flags: dict[str, bool], action_type: str, claims: list[str]
) -> None:
    assert await catalog.match(make_profile(flags), action_type, claims) is None


@pytest.mark.parametrize("action_type", ["payment", "fx", "deposit", "payroll", "dashboard"])
async def test_closed_client_gets_no_offers(catalog: ProductCatalog, action_type: str) -> None:
    profile = make_profile(ALL_FLAGS, cl_type="CLOSE_CLIENT")

    assert await catalog.match(profile, action_type, ALL_CLAIMS) is None


async def test_first_matching_rule_wins(catalog: ProductCatalog) -> None:
    offer = await catalog.match(make_profile(ALL_FLAGS), "payment", ALL_CLAIMS)

    assert offer is not None
    assert offer.rule_id == "letter_of_credit"
