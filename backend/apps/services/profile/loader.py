import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from apps.services.profile.config import ProfileConfig
from apps.services.profile.okved import normalize

MARK_ON = "1.0"
COUNTRY_SEPARATOR = ","


@dataclass(frozen=True)
class Company:
    client_id: str
    group_id: str
    okved_code: str
    okved_name: str
    region: str
    city: str
    revenue_rub: float
    workers: str
    company_age: str
    eco_stage: str | None
    ownership: str
    client_type: str
    products: tuple[str, ...]
    import_countries: tuple[str, ...]
    importer: bool
    negative_mark: bool


@dataclass(frozen=True)
class Companies:
    by_id: dict[str, Company]
    placeholders: frozenset[str]


def parse_countries(raw: str) -> tuple[str, ...]:
    return tuple(name.strip() for name in raw.split(COUNTRY_SEPARATOR) if name.strip())


def parse_row(row: dict[str, str], config: ProfileConfig) -> Company:
    return Company(
        client_id=row["SYNTHETIC_U"],
        group_id=row["GROUP_ID"],
        okved_code=normalize(row["MAINOKVED_CODE"]),
        okved_name=row["MAINOKVED_NAME"],
        region=row["REGION"],
        city=row["CITY"],
        revenue_rub=float(row["REVENUE_COMPANY"]),
        workers=row["AMOUNT_WORKERS_FNS_GRADATION"],
        company_age=row["COMPANY_AGE_YEARS_GRADATION"],
        eco_stage=row["ECO_MARK_LABEL"] or None,
        ownership=row["OKFS_NAME"],
        client_type=row["CL_TYPE"],
        products=tuple(name for column, name in config.products.items() if row[column] == MARK_ON),
        import_countries=parse_countries(row["FTS_COUNTRY_NAME"]),
        importer=row["FTS_FLAG"] == MARK_ON,
        negative_mark=row["NEGATIVEMARK"] == MARK_ON,
    )


def load_companies(path: Path, config: ProfileConfig) -> Companies:
    with path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file, delimiter=";"))
    counts = Counter(row["SYNTHETIC_U"] for row in rows)
    placeholders = frozenset(client_id for client_id, count in counts.items() if count > 1)
    by_id = {
        row["SYNTHETIC_U"]: parse_row(row, config)
        for row in rows
        if row["SYNTHETIC_U"] not in placeholders
    }
    return Companies(by_id=by_id, placeholders=placeholders)
