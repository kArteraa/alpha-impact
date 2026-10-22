import csv
import json
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import cache, cached_property
from pathlib import Path

from pydantic import BaseModel

from apps.services.counterparty.config import load_config
from apps.services.counterparty.loader import CSV_DELIMITER, load_cards, read_payments
from apps.services.products.catalog import RULES_PATH, load_catalog
from scripts.seed import RAW_DIR, SEED_DIR
from shared.config.clients import SERVED_CLIENTS

CONFIG = load_config()
PAYMENTS_FILE = RAW_DIR / CONFIG.payments_file
UNKNOWN_COMPANY = "U_999999999"
UNKNOWN_INN = "7707083893"
COMPANY_ID = re.compile(r"U_\d+")
PERSON_ID = re.compile(r"F_\d+")
MACHINE_VALUE = re.compile(
    r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
    r"|\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:\d{2})?)?"
)
SEPARATORS = " \N{NO-BREAK SPACE}\N{NARROW NO-BREAK SPACE}"
WITHOUT_SEPARATORS = str.maketrans("", "", SEPARATORS)
NUMBER = re.compile(
    rf"(?<![0-9A-Za-z_.,])(?:\d{{1,3}}(?:[{SEPARATORS},]\d{{3}})+|\d+)(?:[.,]\d+)?(?![0-9A-Za-z_])"
)
COMMA_GROUPS = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d+)?")
MIN_AMOUNT = 10_000
PRODUCT_MARKS = ("CL_PRODUCT_", "FACTORING_MARK")
PRODUCT_LABELS = frozenset(rule.product.casefold() for rule in load_catalog(RULES_PATH).rules)
OWN_OFFER = frozenset({"product_offer"})

Probe = tuple[str | None, str | None]


@dataclass(frozen=True)
class ForeignData:
    counterparties: frozenset[str] = frozenset()
    amounts: frozenset[float] = frozenset()
    own: frozenset[str] = frozenset()

    @cached_property
    def amount_keys(self) -> frozenset[int]:
        return amount_keys(self.amounts)

    def has_amount(self, value: float) -> bool:
        return not amount_keys([value]).isdisjoint(self.amount_keys)


def amount_keys(values: Iterable[float]) -> frozenset[int]:
    return frozenset(
        key for value in values if value >= MIN_AMOUNT for key in (int(value), round(value))
    )


def seed_clients() -> dict[str, str]:
    users = json.loads((SEED_DIR / "users.json").read_text(encoding="utf-8"))
    return {client: user["id"] for user in users for client in user["clients"]}


def client_groups(path: Path, clients: Iterable[str]) -> dict[str, frozenset[str]]:
    members: defaultdict[str, set[str]] = defaultdict(set)
    group_of: dict[str, str] = {}
    with path.open(encoding="utf-8", newline="") as file:
        for row in csv.DictReader(file, delimiter=CSV_DELIMITER):
            if row["GROUP_ID"]:
                group_of[row["SYNTHETIC_U"]] = row["GROUP_ID"]
                members[row["GROUP_ID"]].add(row["SYNTHETIC_U"])
    return {
        client: frozenset(members.get(group_of.get(client, ""), {client})) for client in clients
    }


@cache
def seed_foreign_data() -> dict[str, ForeignData]:
    cards = load_cards(RAW_DIR / SERVED_CLIENTS.companies_file, CONFIG)
    clients = seed_clients()
    amounts: dict[str, set[float]] = {client: set() for client in clients}
    pairs: defaultdict[tuple[str, str], float] = defaultdict(float)
    received: defaultdict[str, float] = defaultdict(float)
    sent: defaultdict[str, float] = defaultdict(float)
    for payment in read_payments(PAYMENTS_FILE):
        received[payment.beneficiary] += payment.amount
        sent[payment.payer] += payment.amount
        for client, other in (
            (payment.payer, payment.beneficiary),
            (payment.beneficiary, payment.payer),
        ):
            if client in amounts:
                amounts[client].add(payment.amount)
                pairs[client, other] += payment.amount
    counterparties: dict[str, set[str]] = {client: set() for client in clients}
    for (client, other), amount in pairs.items():
        counterparties[client].add(other)
        amounts[client] |= {amount, received[other], sent[other]}
        if other in cards:
            amounts[client].add(cards[other].revenue_rub)
    groups = client_groups(RAW_DIR / SERVED_CLIENTS.companies_file, clients)
    return {
        client: ForeignData(
            frozenset(counterparties[client]), frozenset(amounts[client] - {0.0}), groups[client]
        )
        for client in clients
    }


def probes(foreign: ForeignData, limit: int | None = None) -> list[Probe]:
    return [
        *((company, None) for company in sorted(foreign.counterparties)[:limit]),
        (UNKNOWN_COMPANY, None),
        (None, UNKNOWN_INN),
    ]


def leaves(value: object, skipped: frozenset[str] = frozenset()) -> Iterator[object]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key not in skipped:
                yield key
                yield from leaves(item, skipped)
    elif isinstance(value, list):
        for item in value:
            yield from leaves(item, skipped)
    else:
        yield value


def numbers(text: str) -> Iterator[float]:
    for match in NUMBER.findall(text):
        plain = match.translate(WITHOUT_SEPARATORS)
        if COMMA_GROUPS.fullmatch(plain):
            yield float(plain.replace(",", ""))
        if plain.count(",") + plain.count(".") <= 1:
            yield float(plain.replace(",", "."))


def text_leaks(text: str, own: frozenset[str]) -> list[str]:
    return [
        *(company for company in COMPANY_ID.findall(text) if company not in own),
        *PERSON_ID.findall(text),
        *(mark for mark in PRODUCT_MARKS if mark in text),
    ]


def texts(dumped: object, skipped: frozenset[str] = frozenset()) -> set[str]:
    return {leaf for leaf in leaves(dumped, skipped) if isinstance(leaf, str)}


def assert_no_foreign_data(payload: object, client_id: str, foreign: ForeignData) -> None:
    dumped = payload.model_dump(mode="json") if isinstance(payload, BaseModel) else payload
    leaks = [
        label
        for text in {text.casefold() for text in texts(dumped, OWN_OFFER)}
        for label in PRODUCT_LABELS
        if label in text
    ]
    values = {
        float(leaf)
        for leaf in leaves(dumped)
        if isinstance(leaf, int | float) and not isinstance(leaf, bool)
    }
    own = foreign.own | {client_id}
    for text in {MACHINE_VALUE.sub(" ", text) for text in texts(dumped)}:
        leaks += text_leaks(text, own)
        values.update(numbers(text))
    leaks += [str(value) for value in values if foreign.has_amount(value)]
    assert not leaks, f"{client_id} sees foreign data {leaks} in {type(payload).__name__}"
