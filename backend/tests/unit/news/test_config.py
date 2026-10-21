import pytest
from pydantic import ValidationError

from apps.services.news.config import load_config
from shared.config.factors import FACTORS

CONFIG = load_config()


def test_config_rejects_factor_without_hint() -> None:
    hints = {name: hint for name, hint in CONFIG.factor_hints.items() if name != "key_rate"}

    with pytest.raises(ValidationError, match="factor_hints"):
        type(CONFIG).model_validate({**CONFIG.model_dump(), "factor_hints": hints})


def test_config_rejects_unknown_industry_hint() -> None:
    hints = {**CONFIG.industry_hints, "space": "космос"}

    with pytest.raises(ValidationError, match="industry_hints"):
        type(CONFIG).model_validate({**CONFIG.model_dump(), "industry_hints": hints})


def test_prompt_lists_factors_and_industries() -> None:
    assert all(f"- {name}:" in CONFIG.prompt for name in FACTORS)
    assert all(f"- {name}:" in CONFIG.prompt for name in CONFIG.industry_hints)


def test_config_rejects_missing_product_hint() -> None:
    hints = {"loan": "кредит"}
    with pytest.raises(ValidationError, match="product_hints"):
        type(CONFIG).model_validate({**CONFIG.model_dump(), "product_hints": hints})
