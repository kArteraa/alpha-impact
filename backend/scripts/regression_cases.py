from collections import Counter
from datetime import date
from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, model_validator

from apps.services.interpreter.context import source_key
from apps.services.interpreter.drafting import card_claims
from shared.contracts.schemas import (
    Claim,
    ClaimType,
    FollowupContext,
    HouseViewClaim,
    InsightCard,
    InterpretRequest,
    InterpretResponse,
)

CASES_DIR = Path(__file__).resolve().parents[1] / "tests" / "regression" / "cases"
SourceKind = Literal["news", "house_view", "profile", "graph", "calc"]
ROLE_BLOCKS = ("why_for_you", "actions")


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
        return bool(self.model_dump(exclude_defaults=True, exclude={"silent"}))


class Case(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    title: str
    request: InterpretRequest
    followup_of: str | None = None
    differs_from: str | None = None
    expect: Expectations = Expectations()
    when_card: Expectations = Expectations()

    @model_validator(mode="after")
    def followup_has_parent(self) -> Self:
        is_followup = isinstance(self.request.action_context, FollowupContext)
        if is_followup != (self.followup_of is not None):
            raise ValueError("followup_of is set exactly for followup action contexts")
        if self.followup_of is not None and self.differs_from is not None:
            raise ValueError("a followup case cannot compare roles")
        if self.when_card.silent is not None:
            raise ValueError("when_card is checked only on cards and cannot set silent")
        return self

    def with_parent_card(self, card_id: str) -> InterpretRequest:
        context = self.request.action_context
        assert isinstance(context, FollowupContext)
        followup = context.model_copy(update={"card_id": card_id})
        return self.request.model_copy(update={"action_context": followup})


def load_cases(directory: Path) -> list[Case]:
    cases = [
        Case.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in sorted(directory.glob("*.yaml"))
    ]
    counts = Counter(item.id for item in cases)
    duplicates = sorted(case_id for case_id, count in counts.items() if count > 1)
    if duplicates:
        raise ValueError(f"Duplicate regression case ids: {', '.join(duplicates)}")
    seen: dict[str, Case] = {}
    for item in cases:
        if item.differs_from is not None:
            check_role_pair(item, seen.get(item.differs_from))
        seen[item.id] = item
    return cases


def check_role_pair(case: Case, peer: Case | None) -> None:
    if peer is None:
        raise ValueError(f"Case {case.id} compares roles with no earlier case {case.differs_from}")
    if case.request.role == peer.request.role:
        raise ValueError(f"Case {case.id} compares the same role as {peer.id}")
    if case.request.model_copy(update={"role": peer.request.role}) != peer.request:
        raise ValueError(f"Case {case.id} must repeat the request of {peer.id} except the role")


def bank_claims(card: InsightCard) -> list[Claim]:
    return [item for item in card_claims(card) if item.type is ClaimType.BANK]


def invariant_failures(card: InsightCard, cited: dict[str, HouseViewClaim]) -> list[str]:
    basis = {source_key(source) for source in card.basis}
    failures = [
        f"card {card.id}: claim source {source_key(item.source_ref)} is not in basis"
        for item in card_claims(card)
        if source_key(item.source_ref) not in basis
    ]
    for item in bank_claims(card):
        source = item.source_ref
        view = cited.get(source.id)
        if source.kind != "house_view":
            failures.append(
                f"card {card.id}: bank claim cites {source_key(source)}, not house view"
            )
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
    per_card = [card_failures(card, expect, cited) for card in response.cards]
    if any(not failures for failures in per_card):
        return []
    reasons = "; ".join(failure for failures in per_card for failure in failures)
    return [f"no card meets expectations: {reasons}"]


def role_texts(card: InsightCard) -> dict[str, list[str]]:
    blocks = {"why_for_you": card.why_for_you, "actions": card.actions}
    return {name: [item.text for item in blocks[name]] for name in ROLE_BLOCKS}


def role_failures(case: Case, response: InterpretResponse, peer: InsightCard | None) -> list[str]:
    if peer is None:
        return [f"case {case.differs_from} gave no card to compare roles"]
    if not response.cards:
        return ["expected a card to compare roles, got none"]
    card = response.cards[0]
    mine, theirs = role_texts(card), role_texts(peer)
    return [
        f"card {card.id}: {name} repeats card {peer.id} of {case.differs_from}"
        for name in ROLE_BLOCKS
        if mine[name] == theirs[name]
    ]


def check(
    case: Case,
    response: InterpretResponse,
    cited: dict[str, HouseViewClaim],
    peer: InsightCard | None = None,
) -> list[str]:
    failures = expectation_failures(case.expect, response, cited)
    if case.differs_from is not None:
        failures += role_failures(case, response, peer)
    for card in response.cards:
        failures += invariant_failures(card, cited)
    if response.cards:
        failures += expectation_failures(case.when_card, response, cited)
    return failures
