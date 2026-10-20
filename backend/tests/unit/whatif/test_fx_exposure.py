import pytest

from apps.services.whatif.formulas import fx_exposure


def test_weaker_ruble_makes_payment_more_expensive() -> None:
    result = fx_exposure(1_000_000.0, "USD", 82.0, 87.0)

    assert result.kind == "fx_exposure"
    assert result.unit == "RUB"
    assert result.value == 5_000_000.0
    assert result.formula == "1 000 000 USD × (87 − 82) ₽ = 5 000 000 ₽"
    assert result.assumptions


def test_stronger_ruble_makes_payment_cheaper() -> None:
    result = fx_exposure(250_000.0, "CNY", 12.1, 11.85)

    assert result.value == -62_500.0
    assert result.formula == "250 000 CNY × (11,85 − 12,1) ₽ = −62 500 ₽"


@pytest.mark.parametrize(
    ("amount", "currency"),
    [(0.0, "USD"), (-5.0, "USD"), (100.0, "US"), (100.0, "usd1")],
)
def test_rejects_invalid_input(amount: float, currency: str) -> None:
    with pytest.raises(ValueError):
        fx_exposure(amount, currency, 82.0, 87.0)
