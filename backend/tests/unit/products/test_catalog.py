from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.services.products.catalog import load_catalog
from apps.services.products.service import ProductCatalog
from tests.unit.products.profiles import make_profile

CATALOG = """
vocabulary:
  features: {cl_type: Тип клиента}
  flags: {tenders: Участвует в тендерах}
  claims: {tender_found: Найден подходящий тендер}
exclude:
  features: {cl_type: CLOSE_CLIENT}
rules:
  - id: guarantee
    product: Банковская гарантия
    reason: Тендер требует обеспечения
    action_types: [page]
    flags: [tenders]
    claims: [tender_found]
"""


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "rules.yaml"
    path.write_text(text, encoding="utf-8")
    return path


async def test_rules_are_loaded_from_file(tmp_path: Path) -> None:
    catalog = ProductCatalog(load_catalog(write(tmp_path, CATALOG)))

    offer = await catalog.match(make_profile({"tenders": True}), "page", ["tender_found"])

    assert offer is not None
    assert offer.rule_id == "guarantee"
    assert offer.product == "Банковская гарантия"
    assert offer.reason == "Тендер требует обеспечения"


@pytest.mark.parametrize(
    "broken",
    [
        CATALOG.replace("claims:", "tags:"),
        CATALOG.replace("action_types: [page]", "action_types: []"),
        CATALOG.replace("    product: Банковская гарантия\n", ""),
        CATALOG.replace("action_types: [page]", "action_types: [paymnet]"),
        CATALOG + CATALOG.split("rules:\n")[1],
        CATALOG.replace("flags: [tenders]", "flags: [tender]"),
        CATALOG.replace("claims: [tender_found]", "claims: [tender_find]"),
        CATALOG.replace("features: {cl_type: CLOSE_CLIENT}", "features: {CL_TYPE: CLOSE_CLIENT}"),
    ],
)
def test_malformed_catalog_is_rejected(tmp_path: Path, broken: str) -> None:
    with pytest.raises(ValidationError):
        load_catalog(write(tmp_path, broken))
