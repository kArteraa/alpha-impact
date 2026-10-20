import pytest

from apps.services.whatif.formatting import format_amount, format_rate


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (100_000_000.0, "100 000 000"),
        (1_726_027.397, "1 726 027,40"),
        (-500_000.0, "−500 000"),
        (999.0, "999"),
        (0.5, "0,50"),
        (0.0, "0"),
    ],
)
def test_format_amount(value: float, expected: str) -> None:
    assert format_amount(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (14.0, "14"),
        (13.5, "13,5"),
        (87.35, "87,35"),
        (13.125, "13,125"),
        (0.1712, "0,1712"),
        (1500.5, "1 500,5"),
        (0.0, "0"),
        (-0.25, "−0,25"),
    ],
)
def test_format_rate(value: float, expected: str) -> None:
    assert format_rate(value) == expected


def test_format_rate_hides_float_noise() -> None:
    assert format_rate(0.1 + 0.2) == "0,3"
    assert format_rate(13.5 + 0.1 + 0.2) == "13,8"


def test_format_rate_sign_follows_rounded_value() -> None:
    assert format_rate(-1e-12) == "0"
