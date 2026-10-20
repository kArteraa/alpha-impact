import csv
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from apps.services.counterparty.config import CounterpartyConfig
from shared.config.industries import INDUSTRIES, industry_class, normalize_okved

CSV_DELIMITER = ";"


@dataclass(frozen=True)
class Card:
    industry_class: str
    region: str
    size_bucket: str
    revenue_rub: float


@dataclass(frozen=True, slots=True)
class Payment:
    payer: str
    beneficiary: str
    amount: float
    count: int


def size_bucket(revenue_rub: float, config: CounterpartyConfig) -> str:
    for bucket in config.size_buckets:
        if revenue_rub <= bucket.max_revenue_rub:
            return bucket.name
    return config.largest_bucket


def parse_card(row: dict[str, str], config: CounterpartyConfig) -> Card:
    revenue = float(row["REVENUE_COMPANY"])
    return Card(
        industry_class=industry_class(normalize_okved(row["MAINOKVED_CODE"]), INDUSTRIES),
        region=row["REGION"],
        size_bucket=size_bucket(revenue, config),
        revenue_rub=revenue,
    )


def load_cards(path: Path, config: CounterpartyConfig) -> dict[str, Card]:
    cards: dict[str, Card] = {}
    repeated: set[str] = set()
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file, delimiter=CSV_DELIMITER):
            company_id = row["SYNTHETIC_U"]
            if company_id in cards:
                repeated.add(company_id)
            cards[company_id] = parse_card(row, config)
    return {company_id: card for company_id, card in cards.items() if company_id not in repeated}


def read_payments(path: Path) -> Iterator[Payment]:
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file, delimiter=CSV_DELIMITER):
            payment = Payment(
                payer=row["PAYER"],
                beneficiary=row["BENEFICIARY"],
                amount=float(row["PAY_AMT"]),
                count=int(float(row["PAY_CNT"])),
            )
            if payment.payer != payment.beneficiary and payment.amount > 0:
                yield payment
