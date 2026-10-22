from collections.abc import Mapping
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.regression_cases import CASES_DIR, Case, check, load_cases
from shared.contracts.schemas import ClaimType, ProductOffer, SourceRef
from tests.regression_data import (
    CITED,
    NEWS,
    OLD_RATE,
    PROFILE,
    RATE,
    SILENT,
    answer,
    card,
    claim,
    house_view,
)


def case(expect: Mapping[str, object] | None = None, **fields: object) -> Case:
    payload: dict[str, object] = {
        "id": "case",
        "title": "Кейс",
        "request": {
            "user_id": "user",
            "client_id": "U_1",
            "role": "cfo",
            "action_context": {"type": "deposit", "amount": 1_000_000, "term_days": 90},
        },
        "expect": expect or {},
        **fields,
    }
    return Case.model_validate(payload)


def test_catalog_has_ten_valid_cases() -> None:
    cases = load_cases(CASES_DIR)

    assert len(cases) == 10


def test_every_catalog_case_expects_something() -> None:
    for item in load_cases(CASES_DIR):
        assert item.expect.is_set() or item.when_card.is_set(), item.id


def test_followup_cases_point_to_an_earlier_case() -> None:
    seen: set[str] = set()
    followups = 0
    for item in load_cases(CASES_DIR):
        if item.followup_of is not None:
            followups += 1
            assert item.followup_of in seen, item.id
        seen.add(item.id)
    assert followups >= 1


def test_followup_of_requires_followup_context() -> None:
    with pytest.raises(ValidationError):
        case(followup_of="other")


def test_followup_context_requires_followup_of() -> None:
    with pytest.raises(ValidationError):
        case(
            request={
                "user_id": "user",
                "client_id": "U_1",
                "role": "cfo",
                "action_context": {"type": "followup", "card_id": "", "question": "Почему?"},
            }
        )


def test_unknown_expectation_is_rejected() -> None:
    with pytest.raises(ValidationError):
        case({"silnet": True})


def test_load_cases_rejects_duplicate_ids(tmp_path: Path) -> None:
    text = (
        "id: same\ntitle: Кейс\nrequest:\n  user_id: u\n  client_id: c\n  role: cfo\n"
        "  action_context: {type: dashboard}\nexpect: {silent: true}\n"
    )
    (tmp_path / "01.yaml").write_text(text, encoding="utf-8")
    (tmp_path / "02.yaml").write_text(text, encoding="utf-8")

    with pytest.raises(ValueError, match="same"):
        load_cases(tmp_path)


def test_matching_card_passes() -> None:
    expect = {
        "silent": False,
        "bank_subject": "key_rate",
        "bank_date": "2026-09-11",
        "basis_kinds": ["news", "house_view", "profile"],
        "needs_review": False,
    }

    assert check(case(expect), answer(card()), CITED) == []


def test_expected_silence_fails_on_card() -> None:
    assert check(case({"silent": True}), answer(card()), CITED) != []


def test_expected_card_fails_on_silence() -> None:
    assert check(case({"silent": False}), SILENT, CITED) != []


def test_card_expectation_fails_on_silence() -> None:
    assert check(case({"bank_subject": "key_rate"}), SILENT, CITED) != []


def test_silence_passes_when_expected() -> None:
    assert check(case({"silent": True}), SILENT, CITED) == []


def test_claim_source_missing_from_basis_fails() -> None:
    assert check(case(), answer(card(basis=[NEWS, RATE])), CITED) != []


def test_bank_claim_without_house_view_source_fails() -> None:
    bank_from_news = card(bank_view=[claim(NEWS, ClaimType.BANK)], basis=[NEWS, PROFILE])
    cited = {**CITED, NEWS.id: house_view(NEWS.id)}

    assert check(case(), answer(bank_from_news), cited) != []


def test_bank_claim_with_unknown_house_view_fails() -> None:
    unknown = SourceRef(kind="house_view", id="hv-missing")
    lost = card(bank_view=[claim(unknown, ClaimType.BANK)], basis=[NEWS, PROFILE, unknown])

    assert check(case(), answer(lost), CITED) != []


def test_bank_claim_citing_superseded_view_fails() -> None:
    stale = card(bank_view=[claim(OLD_RATE, ClaimType.BANK)], basis=[NEWS, PROFILE, OLD_RATE])

    assert check(case(), answer(stale), CITED) != []


def test_other_bank_subject_fails() -> None:
    assert check(case({"bank_subject": "inflation"}), answer(card()), CITED) != []


def test_other_bank_date_fails() -> None:
    assert check(case({"bank_date": "2026-07-31"}), answer(card()), CITED) != []


def test_subject_and_date_must_match_one_claim() -> None:
    inflation = SourceRef(kind="house_view", id="hv-inflation")
    cited = {
        **CITED,
        "hv-rate": house_view("hv-rate", day=date(2026, 9, 7)),
        "hv-inflation": house_view("hv-inflation", subject="inflation"),
    }
    mixed = card(
        bank_view=[claim(RATE, ClaimType.BANK), claim(inflation, ClaimType.BANK)],
        basis=[NEWS, PROFILE, RATE, inflation],
    )
    expect = {"bank_subject": "key_rate", "bank_date": "2026-09-11"}

    assert check(case(expect), answer(mixed), cited) != []


def test_missing_basis_kind_fails() -> None:
    assert check(case({"basis_kinds": ["graph"]}), answer(card()), CITED) != []


def test_needs_review_mismatch_fails() -> None:
    reviewed = card(needs_review=True)

    assert check(case({"needs_review": False}), answer(reviewed), CITED) != []


def test_product_mismatch_fails() -> None:
    offer = ProductOffer(product="Депозит", reason="Остатки", rule_id="deposit")

    assert check(case({"product": "Факторинг"}), answer(card(product_offer=offer)), CITED) != []
    assert check(case({"product": "Факторинг"}), answer(card()), CITED) != []
    assert check(case({"product": "Депозит"}), answer(card(product_offer=offer)), CITED) == []


def test_when_card_is_skipped_on_silence() -> None:
    assert check(case(when_card={"basis_kinds": ["graph"]}), SILENT, CITED) == []


def test_when_card_applies_to_card() -> None:
    assert check(case(when_card={"basis_kinds": ["graph"]}), answer(card()), CITED) != []


def test_invariants_apply_without_expectations() -> None:
    assert check(case(), answer(card(basis=[])), CITED) != []


def test_expectations_hold_for_every_card() -> None:
    other = card(id="card-2", bank_view=[], basis=[NEWS, PROFILE])

    assert check(case({"bank_subject": "key_rate"}), answer(card(), other), CITED) != []


def test_failure_names_the_source() -> None:
    failures = check(case(), answer(card(basis=[NEWS, RATE])), CITED)

    assert any("profile:industry_class" in failure for failure in failures)
