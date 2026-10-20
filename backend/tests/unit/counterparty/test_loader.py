import pytest

from apps.services.counterparty.config import load_config
from apps.services.counterparty.loader import Card, load_cards, read_payments, size_bucket
from tests.unit.counterparty.fixtures import CLIENT, COMPANIES_CSV, PAYMENTS_CSV


def test_cards_carry_industry_region_and_size() -> None:
    cards = load_cards(COMPANIES_CSV, load_config())

    assert cards["U_902"] == Card(
        industry_class="logistics", region="Санкт-Петербург", size_bucket="small", revenue_rub=5e8
    )
    assert cards["U_904"].industry_class == "wholesale"
    assert cards[CLIENT].size_bucket == "largest"


def test_repeated_id_has_no_card() -> None:
    assert "U_909" not in load_cards(COMPANIES_CSV, load_config())


@pytest.mark.parametrize(
    ("revenue", "expected"),
    [
        (5e7, "micro"),
        (1.2e8, "micro"),
        (5e8, "small"),
        (1.5e9, "medium"),
        (3e9, "large"),
        (1.5e10, "large"),
        (2e10, "largest"),
    ],
)
def test_size_bucket_by_revenue(revenue: float, expected: str) -> None:
    assert size_bucket(revenue, load_config()) == expected


def test_self_and_empty_payments_are_dropped() -> None:
    payments = list(read_payments(PAYMENTS_CSV))

    assert len(payments) == 7
    assert all(payment.payer != payment.beneficiary for payment in payments)
    assert all(payment.amount > 0 for payment in payments)
