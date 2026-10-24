import pytest

from shared.config.industries import INDUSTRIES, industry_class, normalize_okved


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("41.2", "41.20"),
        ("46.4", "46.40"),
        ("68.3", "68.30"),
        ("41.20", "41.20"),
        ("68.20.2", "68.20.2"),
        ("45.31.1", "45.31.1"),
        ("99", "99"),
        (" 41.2 ", "41.20"),
    ],
)
def test_normalize_pads_one_digit_group(raw: str, expected: str) -> None:
    assert normalize_okved(raw) == expected


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("45.11.2", "auto_dealer"),
        ("45.31.1", "wholesale"),
        ("46.49", "wholesale"),
        ("46.71.2", "fuel"),
        ("46.21", "agro"),
        ("46.46", "pharma"),
        ("41.20.9", "construction"),
        ("42.99", "construction"),
        ("68.30", "real_estate"),
        ("64.91.2", "leasing"),
        ("64.19", "finance"),
        ("99.99", "other"),
    ],
)
def test_industry_class_takes_longest_prefix(code: str, expected: str) -> None:
    assert industry_class(code, INDUSTRIES) == expected


def test_industries_cannot_be_changed_at_runtime() -> None:
    with pytest.raises(TypeError):
        INDUSTRIES["46.49"] = "other"  # type: ignore[index]


def test_prefix_matches_whole_groups_only() -> None:
    assert industry_class("10.11", {"1": "x", "10": "food"}) == "food"
    assert industry_class("46.7", {"46.71": "fuel", "46": "wholesale"}) == "wholesale"
