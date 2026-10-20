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
