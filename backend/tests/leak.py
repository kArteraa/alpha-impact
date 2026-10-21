import json
import re
from collections import defaultdict
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
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
NUMBER = re.compile(r"(?<![\w.,])(?:\d{1,3}(?:[  ]\d{3})+|\d+)(?:[.,]\d+)?(?!\w)")
PRODUCT_MARKS = ("CL_PRODUCT_", "FACTORING_MARK")
PRODUCT_LABELS = frozenset(rule.product.casefold() for rule in load_catalog(RULES_PATH).rules)
OWN_OFFER = "product_offer"

Probe = tuple[str | None, str | None]


@dataclass
class ForeignData:
    recipients: set[str] = field(default_factory=set)
    amounts: set[float] = field(default_factory=set)


def seed_clients() -> dict[str, str]:
    users = json.loads((SEED_DIR / "users.json").read_text(encoding="utf-8"))
    return {client: user["id"] for user in users for client in user["clients"]}


@cache
def seed_foreign_data() -> dict[str, ForeignData]:
    cards = load_cards(RAW_DIR / SERVED_CLIENTS.companies_file, CONFIG)
    foreign = {client: ForeignData() for client in seed_clients()}
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
            if client in foreign:
                foreign[client].amounts.add(payment.amount)
                pairs[client, other] += payment.amount
        if payment.payer in foreign:
            foreign[payment.payer].recipients.add(payment.beneficiary)
    for (client, other), amount in pairs.items():
        foreign[client].amounts |= {amount, received[other], sent[other]}
        if other in cards:
            foreign[client].amounts.add(cards[other].revenue_rub)
    for data in foreign.values():
        data.amounts.discard(0.0)
    return foreign


def probes(foreign: ForeignData) -> list[Probe]:
    return [
        *((recipient, None) for recipient in sorted(foreign.recipients)),
        (UNKNOWN_COMPANY, None),
        (None, UNKNOWN_INN),
    ]


def leaves(value: object) -> Iterator[object]:
    if isinstance(value, dict):
        for key, item in value.items():
            if key != OWN_OFFER:
                yield key
                yield from leaves(item)
    elif isinstance(value, list):
        for item in value:
            yield from leaves(item)
    else:
        yield value


def numbers(text: str) -> Iterator[float]:
    for match in NUMBER.findall(text):
        yield float(re.sub(r"[  ]", "", match).replace(",", "."))


def text_leaks(text: str, client_id: str) -> list[str]:
    folded = text.casefold()
    return [
        *(company for company in COMPANY_ID.findall(text) if company != client_id),
        *PERSON_ID.findall(text),
        *(mark for mark in PRODUCT_MARKS if mark in text),
        *(label for label in PRODUCT_LABELS if label in folded),
    ]


def assert_no_foreign_data(payload: BaseModel, client_id: str, foreign: ForeignData) -> None:
    leaks: list[str] = []
    for leaf in leaves(payload.model_dump(mode="json")):
        values: Iterable[float] = ()
        if isinstance(leaf, str):
            leaks += text_leaks(leaf, client_id)
            values = numbers(leaf)
        elif isinstance(leaf, int | float):
            values = (float(leaf),)
        leaks += [str(value) for value in values if value in foreign.amounts]
    assert not leaks, f"{client_id} sees foreign data {leaks} in {payload!r}"
