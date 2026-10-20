import pytest

from apps.services.whatif.formulas import deposit_terms


def test_fixing_rate_beats_rolling_on_falling_path() -> None:
    result = deposit_terms(50_000_000.0, 90, [14.0, 13.5, 13.0])

    assert result.kind == "deposit_terms"
    assert result.unit == "RUB"
    assert result.value == 61_643.84
    assert result.formula == (
        "фиксация: 50 000 000 ₽ × 14% × 90/365 = 1 726 027,40 ₽; "
        "переразмещение: 50 000 000 ₽ × (14% × 30 + 13,5% × 30 + 13% × 30)/365"
        " = 1 664 383,56 ₽; разница 61 643,84 ₽"
    )
    assert result.assumptions


def test_last_month_uses_remaining_days_and_extra_path_is_ignored() -> None:
    result = deposit_terms(10_000_000.0, 45, [12.0, 14.0, 20.0])

    assert result.value == -8_219.17
    assert "(12% × 30 + 14% × 15)/365" in result.formula
    assert "= 147 945,21 ₽" in result.formula
    assert "= 156 164,38 ₽; разница −8 219,17 ₽" in result.formula


def test_flat_path_gives_zero_difference() -> None:
    assert deposit_terms(10_000_000.0, 180, [14.0] * 6).value == 0.0


@pytest.mark.parametrize(
    ("amount", "term_days", "rate_path"),
    [
        (0.0, 90, [14.0, 14.0, 14.0]),
        (1_000_000.0, 0, [14.0]),
        (1_000_000.0, 91, [14.0, 14.0, 14.0]),
        (1_000_000.0, 30, []),
    ],
)
def test_rejects_invalid_input(amount: float, term_days: int, rate_path: list[float]) -> None:
    with pytest.raises(ValueError):
        deposit_terms(amount, term_days, rate_path)


@pytest.mark.parametrize(
    "rate_path",
    [[14.0, float("nan"), 13.0], [14.0, -1.0, 13.0], [float("inf"), 13.5, 13.0]],
)
def test_rejects_invalid_rates(rate_path: list[float]) -> None:
    with pytest.raises(ValueError):
        deposit_terms(1_000_000.0, 90, rate_path)
