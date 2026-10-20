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


def test_rejects_ruble_as_foreign_currency() -> None:
    with pytest.raises(ValueError):
        fx_exposure(100.0, "RUB", 1.0, 1.0)


@pytest.mark.parametrize(
    ("amount", "rate_now", "rate_forecast"),
    [(float("nan"), 82.0, 87.0), (100.0, 82.0, -87.0), (100.0, float("inf"), 87.0)],
)
def test_rejects_non_finite_or_negative_values(
    amount: float, rate_now: float, rate_forecast: float
) -> None:
    with pytest.raises(ValueError):
        fx_exposure(amount, "USD", rate_now, rate_forecast)


def test_sub_ruble_rates_keep_significant_digits() -> None:
    result = fx_exposure(10_000_000.0, "KZT", 0.1712, 0.1745)

    assert result.value == 33_000.0
    assert result.formula == "10 000 000 KZT × (0,1745 − 0,1712) ₽ = 33 000 ₽"


def test_rejects_zero_exchange_rate() -> None:
    with pytest.raises(ValueError):
        fx_exposure(100.0, "USD", 0.0, 87.0)
