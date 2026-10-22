from datetime import date
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from shared.contracts.schemas import (
    Claim,
    ClaimType,
    FollowupContext,
    HouseViewClaim,
    InsightCard,
    InterpretRequest,
    InterpretResponse,
    SourceRef,
)

CASES_DIR = Path(__file__).resolve().parents[1] / "tests" / "regression" / "cases"
SourceKind = Literal["news", "house_view", "profile", "graph", "calc"]


class Expectations(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    silent: bool | None = None
    bank_subject: str | None = None
    bank_date: date | None = None
    basis_kinds: tuple[SourceKind, ...] = ()
    needs_review: bool | None = None
    product: str | None = None

    def is_set(self) -> bool:
        return bool(self.model_dump(exclude_defaults=True))

    def needs_card(self) -> bool:
        return self.model_copy(update={"silent": None}).is_set()


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    request: InterpretRequest
    followup_of: str | None = None
    expect: Expectations = Expectations()
    when_card: Expectations = Expectations()

    @model_validator(mode="after")
    def followup_has_parent(self) -> Self:
        is_followup = isinstance(self.request.action_context, FollowupContext)
        if is_followup != (self.followup_of is not None):
            raise ValueError("followup_of is set exactly for followup action contexts")
        return self


def load_cases(directory: Path) -> list[Case]:
    cases = [
        Case.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in sorted(directory.glob("*.yaml"))
    ]
    ids = [item.id for item in cases]
    duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"Duplicate regression case ids: {', '.join(duplicates)}")
    return cases


def all_claims(card: InsightCard) -> list[Claim]:
    return [
        *card.what_happened,
        *card.why_for_you,
        *card.consequences,
        *card.actions,
        *card.bank_view,
    ]


def bank_claims(card: InsightCard) -> list[Claim]:
    return [item for item in all_claims(card) if item.type is ClaimType.BANK]


def ref(source: SourceRef) -> str:
    return f"{source.kind}:{source.id}"


def invariant_failures(card: InsightCard, cited: dict[str, HouseViewClaim]) -> list[str]:
    basis = {ref(source) for source in card.basis}
    failures = [
        f"card {card.id}: claim source {ref(item.source_ref)} is not in basis"
        for item in all_claims(card)
        if ref(item.source_ref) not in basis
    ]
    for item in bank_claims(card):
        source = item.source_ref
        view = cited.get(source.id)
        if source.kind != "house_view":
            failures.append(f"card {card.id}: bank claim cites {ref(source)}, not house view")
        elif view is None:
            failures.append(f"card {card.id}: bank claim cites unknown house view {source.id}")
        elif view.status != "approved" or view.superseded_by is not None:
            failures.append(f"card {card.id}: bank claim cites {view.status} house view {view.id}")
    return failures


def matches_bank(item: Claim, expect: Expectations, cited: dict[str, HouseViewClaim]) -> bool:
    view = cited.get(item.source_ref.id) if item.source_ref.kind == "house_view" else None
    if view is None:
        return False
    subject_ok = expect.bank_subject is None or view.subject == expect.bank_subject
    date_ok = expect.bank_date is None or view.date == expect.bank_date
    return subject_ok and date_ok


def card_failures(
    card: InsightCard, expect: Expectations, cited: dict[str, HouseViewClaim]
) -> list[str]:
    failures: list[str] = []
    wants_bank = expect.bank_subject is not None or expect.bank_date is not None
    if wants_bank and not any(matches_bank(item, expect, cited) for item in bank_claims(card)):
        failures.append(
            f"card {card.id}: no bank claim with subject={expect.bank_subject} "
            f"date={expect.bank_date}"
        )
    kinds = {source.kind for source in card.basis}
    missing = [kind for kind in expect.basis_kinds if kind not in kinds]
    if missing:
        failures.append(f"card {card.id}: basis has no {', '.join(missing)}")
    if expect.needs_review is not None and card.needs_review != expect.needs_review:
        failures.append(f"card {card.id}: needs_review={card.needs_review}")
    offered = card.product_offer.product if card.product_offer else None
    if expect.product is not None and offered != expect.product:
        failures.append(f"card {card.id}: product_offer={offered}")
    return failures


def expectation_failures(
    expect: Expectations, response: InterpretResponse, cited: dict[str, HouseViewClaim]
) -> list[str]:
    if expect.silent is not None and response.silent != expect.silent:
        return [f"expected silent={expect.silent}, got silent={response.silent}"]
    if not response.cards:
        return ["expected a card, got none"] if expect.needs_card() else []
    return [failure for card in response.cards for failure in card_failures(card, expect, cited)]


def check(case: Case, response: InterpretResponse, cited: dict[str, HouseViewClaim]) -> list[str]:
    failures = expectation_failures(case.expect, response, cited)
    for card in response.cards:
        failures += invariant_failures(card, cited)
    if response.cards:
        failures += expectation_failures(case.when_card, response, cited)
    return failures
