import pytest

from apps.services.whatif.formulas import rate_burden


def test_rate_cut_saves_interest_over_a_year() -> None:
    result = rate_burden(100_000_000.0, 14.0, 13.5, 12)

    assert result.kind == "rate_burden"
    assert result.unit == "RUB"
    assert result.value == -500_000.0
    assert result.formula == "100 000 000 ₽ × (13,5% − 14%) × 12/12 мес. = −500 000 ₽"
    assert result.assumptions


def test_rate_hike_over_half_year_adds_cost() -> None:
    result = rate_burden(30_000_000.0, 14.0, 16.0, 6)

    assert result.value == 300_000.0
    assert result.formula == "30 000 000 ₽ × (16% − 14%) × 6/12 мес. = 300 000 ₽"


def test_value_rounded_to_kopecks() -> None:
    assert rate_burden(1_000_000.0, 14.0, 13.75, 7).value == -1_458.33


@pytest.mark.parametrize(
    ("amount", "months"),
    [(0.0, 12), (-1.0, 12), (1_000_000.0, 0)],
)
def test_rejects_non_positive_input(amount: float, months: int) -> None:
    with pytest.raises(ValueError):
        rate_burden(amount, 14.0, 13.5, months)


@pytest.mark.parametrize(
    ("amount", "rate_now", "rate_expected"),
    [
        (float("nan"), 14.0, 13.5),
        (float("inf"), 14.0, 13.5),
        (1_000_000.0, float("nan"), 13.5),
        (1_000_000.0, 14.0, -13.5),
    ],
)
def test_rejects_non_finite_or_negative_values(
    amount: float, rate_now: float, rate_expected: float
) -> None:
    with pytest.raises(ValueError):
        rate_burden(amount, rate_now, rate_expected, 12)


def test_zero_rate_is_a_valid_scenario() -> None:
    result = rate_burden(50_000_000.0, 0.0, 3.0, 12)

    assert result.value == 1_500_000.0
    assert result.formula == "50 000 000 ₽ × (3% − 0%) × 12/12 мес. = 1 500 000 ₽"


def test_fractional_rate_is_shown_in_full() -> None:
    result = rate_burden(1_000_000_000.0, 14.0, 13.125, 12)

    assert result.value == -8_750_000.0
    assert result.formula == "1 000 000 000 ₽ × (13,125% − 14%) × 12/12 мес. = −8 750 000 ₽"
