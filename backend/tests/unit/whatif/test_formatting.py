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
        (-0.25, "−0,25"),
    ],
)
def test_format_rate(value: float, expected: str) -> None:
    assert format_rate(value) == expected
