from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.services import products
from shared.contracts.ports import ProductRulesService
from shared.di.container import Container
from tests.unit.products.profiles import make_profile


def resolve() -> ProductRulesService:
    container = Container()
    products.register(container)
    return container.resolve(ProductRulesService)


def test_implements_port() -> None:
    assert isinstance(resolve(), ProductRulesService)


async def test_match_returns_offer_through_port() -> None:
    offer = await resolve().match(make_profile({"imports": True}), "fx", ["ruble_weakening"])

    assert offer is not None
    assert offer.rule_id == "fx_hedge"


def test_broken_catalog_fails_at_registration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    broken = tmp_path / "rules.yaml"
    broken.write_text("rules: []\n", encoding="utf-8")
    monkeypatch.setattr(products, "RULES_PATH", broken)

    with pytest.raises(ValidationError):
        products.register(Container())
