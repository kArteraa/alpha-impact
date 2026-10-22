import json
import re
from collections import defaultdict
from collections.abc import Iterator
from dataclasses import dataclass
from functools import cache

from pydantic import BaseModel

from apps.services.counterparty.config import load_config
from apps.services.counterparty.loader import load_cards, read_payments
from apps.services.products.catalog import RULES_PATH, load_catalog
from scripts.seed import RAW_DIR, SEED_DIR
from shared.config.clients import SERVED_CLIENTS

CONFIG = load_config()
PAYMENTS_FILE = RAW_DIR / CONFIG.payments_file
UNKNOWN_COMPANY = "U_999999999"
UNKNOWN_INN = "7707083893"
COMPANY_ID = re.compile(r"U_\d+")
PERSON_ID = re.compile(r"F_\d+")
UUID = re.compile(r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}")
SEPARATORS = " \N{NO-BREAK SPACE}\N{NARROW NO-BREAK SPACE}"
WITHOUT_SEPARATORS = str.maketrans("", "", SEPARATORS)
NUMBER = re.compile(
    rf"(?<![0-9A-Za-z_.,])(?:\d{{1,3}}(?:[{SEPARATORS}]\d{{3}})+|\d+)(?:[.,]\d+)?(?![0-9A-Za-z_])"
)
PRODUCT_MARKS = ("CL_PRODUCT_", "FACTORING_MARK")
PRODUCT_LABELS = frozenset(rule.product.casefold() for rule in load_catalog(RULES_PATH).rules)
OWN_OFFER = frozenset({"product_offer"})

Probe = tuple[str | None, str | None]


@dataclass(frozen=True)
class ForeignData:
    counterparties: frozenset[str] = frozenset()
    amounts: frozenset[float] = frozenset()


def seed_clients() -> dict[str, str]:
    users = json.loads((SEED_DIR / "users.json").read_text(encoding="utf-8"))
    return {client: user["id"] for user in users for client in user["clients"]}


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
    return {
        client: ForeignData(frozenset(counterparties[client]), frozenset(amounts[client] - {0.0}))
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
        yield float(match.translate(WITHOUT_SEPARATORS).replace(",", "."))


def text_leaks(text: str, client_id: str) -> list[str]:
    return [
        *(company for company in COMPANY_ID.findall(text) if company != client_id),
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
    values = {float(leaf) for leaf in leaves(dumped) if isinstance(leaf, int | float)}
    for text in {UUID.sub(" ", text) for text in texts(dumped)}:
        leaks += text_leaks(text, client_id)
        values.update(numbers(text))
    leaks += [str(value) for value in values if value in foreign.amounts]
    assert not leaks, f"{client_id} sees foreign data {leaks}"
