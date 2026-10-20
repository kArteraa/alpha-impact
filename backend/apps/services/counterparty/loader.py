import csv
from collections import Counter
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


def load_cards(path: Path, config: CounterpartyConfig) -> dict[str, Card]:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=CSV_DELIMITER))
    counts = Counter(row["SYNTHETIC_U"] for row in rows)
    return {
        row["SYNTHETIC_U"]: Card(
            industry_class=industry_class(normalize_okved(row["MAINOKVED_CODE"]), INDUSTRIES),
            region=row["REGION"],
            size_bucket=size_bucket(float(row["REVENUE_COMPANY"]), config),
            revenue_rub=float(row["REVENUE_COMPANY"]),
        )
        for row in rows
        if counts[row["SYNTHETIC_U"]] == 1
    }


def read_payments(path: Path) -> Iterator[Payment]:
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file, delimiter=CSV_DELIMITER):
            if row["PAYER"] != row["BENEFICIARY"]:
                yield Payment(
                    payer=row["PAYER"],
                    beneficiary=row["BENEFICIARY"],
                    amount=float(row["PAY_AMT"]),
                    count=int(float(row["PAY_CNT"])),
                )
