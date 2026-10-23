from collections.abc import Mapping
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.services.interpreter.drafting import CLAIM_BLOCKS
from scripts.regression_cases import CASES_DIR, ROLE_BLOCKS, Case, check, load_cases
from shared.contracts.schemas import Claim, ClaimType, InsightCard, ProductOffer, SourceRef
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


def test_catalog_has_twenty_valid_cases() -> None:
    cases = load_cases(CASES_DIR)

    assert len(cases) == 20


def test_catalog_compares_cfo_and_treasurer_cards() -> None:
    cases = {item.id: item for item in load_cases(CASES_DIR)}
    pairs = [item for item in cases.values() if item.differs_from is not None]

    assert len(pairs) >= 2
    for item in cases.values():
        if item.differs_from is None:
            continue
        roles = {item.request.role.value, cases[item.differs_from].request.role.value}
        assert roles == {"cfo", "treasurer"}, item.id


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


def test_expectations_pass_when_one_card_of_several_matches() -> None:
    other = card(id="card-2", bank_view=[], basis=[NEWS, PROFILE])

    assert check(case({"bank_subject": "key_rate"}), answer(other, card()), CITED) == []


def test_expectations_fail_when_no_card_matches_and_name_every_card() -> None:
    first = card(id="card-1", bank_view=[], basis=[NEWS, PROFILE])
    second = card(id="card-2", bank_view=[], basis=[NEWS, PROFILE])

    failures = check(case({"bank_subject": "key_rate"}), answer(first, second), CITED)

    assert len(failures) == 1
    assert "card-1" in failures[0] and "card-2" in failures[0]


def test_expectations_must_meet_in_one_card() -> None:
    with_rate = card(id="card-1")
    with_graph = card(
        id="card-2", bank_view=[], basis=[NEWS, PROFILE, SourceRef(kind="graph", id="segment")]
    )
    expect = {"bank_subject": "key_rate", "basis_kinds": ["graph"]}

    assert check(case(expect), answer(with_rate, with_graph), CITED) != []


def test_invariants_apply_to_every_card() -> None:
    broken = card(id="card-2", basis=[NEWS, RATE])

    assert check(case({"bank_subject": "key_rate"}), answer(card(), broken), CITED) != []


def test_failure_names_the_source() -> None:
    failures = check(case(), answer(card(basis=[NEWS, RATE])), CITED)

    assert any("profile:industry_class" in failure for failure in failures)


def test_when_card_rejects_silent() -> None:
    with pytest.raises(ValidationError):
        case(when_card={"silent": False})


def role_case(case_id: str, role: str, differs_from: str | None = None) -> str:
    lines = [
        f"id: {case_id}",
        "title: Кейс",
        "request:",
        "  user_id: u",
        "  client_id: c",
        f"  role: {role}",
        "  action_context: {type: deposit, amount: 1000, term_days: 90}",
        "expect: {silent: false}",
    ]
    if differs_from is not None:
        lines.append(f"differs_from: {differs_from}")
    return "\n".join(lines) + "\n"


def write_cases(directory: Path, *texts: str) -> None:
    for number, text in enumerate(texts, start=1):
        (directory / f"{number:02d}.yaml").write_text(text, encoding="utf-8")


def test_load_cases_accepts_role_pair(tmp_path: Path) -> None:
    write_cases(tmp_path, role_case("cfo", "cfo"), role_case("treasurer", "treasurer", "cfo"))

    assert [item.differs_from for item in load_cases(tmp_path)] == [None, "cfo"]


def test_load_cases_rejects_role_pair_to_unknown_case(tmp_path: Path) -> None:
    write_cases(tmp_path, role_case("treasurer", "treasurer", "missing"))

    with pytest.raises(ValueError, match="missing"):
        load_cases(tmp_path)


def test_load_cases_rejects_role_pair_to_later_case(tmp_path: Path) -> None:
    write_cases(tmp_path, role_case("treasurer", "treasurer", "cfo"), role_case("cfo", "cfo"))

    with pytest.raises(ValueError, match="treasurer"):
        load_cases(tmp_path)


def test_load_cases_rejects_role_pair_with_same_role(tmp_path: Path) -> None:
    write_cases(tmp_path, role_case("cfo", "cfo"), role_case("again", "cfo", "cfo"))

    with pytest.raises(ValueError, match="again"):
        load_cases(tmp_path)


def test_load_cases_rejects_role_pair_with_other_request(tmp_path: Path) -> None:
    other = role_case("treasurer", "treasurer", "cfo").replace("amount: 1000", "amount: 2000")
    write_cases(tmp_path, role_case("cfo", "cfo"), other)

    with pytest.raises(ValueError, match="treasurer"):
        load_cases(tmp_path)


def test_differs_from_is_not_allowed_on_followup() -> None:
    with pytest.raises(ValidationError):
        case(
            followup_of="parent",
            differs_from="parent",
            request={
                "user_id": "user",
                "client_id": "U_1",
                "role": "treasurer",
                "action_context": {"type": "followup", "card_id": "", "question": "Почему?"},
            },
        )


def role_card(card_id: str, why: list[str], actions: list[str]) -> InsightCard:
    return card(
        id=card_id,
        why_for_you=[Claim(text=text, type=ClaimType.AI, source_ref=PROFILE) for text in why],
        actions=[Claim(text=text, type=ClaimType.AI, source_ref=PROFILE) for text in actions],
    )


def about(item: InsightCard, news: SourceRef) -> InsightCard:
    return item.model_copy(update={"what_happened": [claim(news)], "basis": [news, PROFILE, RATE]})


OTHER_NEWS = SourceRef(kind="news", id="n2", title="Другая", url="https://n.example/2")
CFO_CARD = role_card(
    "card-cfo", ["Ставка дорожит долг", "План долга"], ["Пересчитать план заимствований"]
)
TREASURER = role_card("card-t", ["Остатки выгоднее держать"], ["Сдвинуть платёжный календарь"])


def test_role_pair_passes_when_why_and_actions_differ() -> None:
    assert check(case(differs_from="cfo"), answer(TREASURER), CITED, (CFO_CARD,)) == []


def test_role_pair_fails_when_one_why_claim_repeats() -> None:
    treasurer = role_card(
        "card-t", ["Остатки выгоднее держать", "План долга"], ["Сдвинуть платёжный календарь"]
    )

    failures = check(case(differs_from="cfo"), answer(treasurer), CITED, (CFO_CARD,))

    assert len(failures) == 1
    assert "why_for_you" in failures[0] and "План долга" in failures[0]


def test_role_pair_fails_when_one_action_repeats() -> None:
    treasurer = role_card(
        "card-t",
        ["Остатки выгоднее держать"],
        ["Сдвинуть платёжный календарь", "Пересчитать план заимствований"],
    )

    failures = check(case(differs_from="cfo"), answer(treasurer), CITED, (CFO_CARD,))

    assert len(failures) == 1
    assert "actions" in failures[0]


def test_role_pair_fails_without_peer_cards() -> None:
    failures = check(case(differs_from="cfo"), answer(TREASURER), CITED, ())

    assert failures == ["case cfo gave no green card to compare roles"]


def test_role_pair_fails_on_silence() -> None:
    assert check(case(differs_from="cfo"), SILENT, CITED, (CFO_CARD,)) != []


def test_role_pair_matches_cards_by_event_news_in_any_order() -> None:
    peers = (about(CFO_CARD, OTHER_NEWS), CFO_CARD)
    response = answer(TREASURER, about(TREASURER.model_copy(update={"id": "card-t2"}), OTHER_NEWS))

    assert check(case(differs_from="cfo"), response, CITED, peers) == []


def test_role_pair_passes_when_one_matched_pair_differs() -> None:
    peers = (CFO_CARD, about(CFO_CARD.model_copy(update={"id": "card-cfo2"}), OTHER_NEWS))
    same = about(CFO_CARD.model_copy(update={"id": "card-t2"}), OTHER_NEWS)

    assert check(case(differs_from="cfo"), answer(same, TREASURER), CITED, peers) == []


def test_role_pair_fails_when_no_card_is_about_the_same_event() -> None:
    failures = check(
        case(differs_from="cfo"), answer(about(TREASURER, OTHER_NEWS)), CITED, (CFO_CARD,)
    )

    assert failures == ["no card has the same what_happened news as a card of cfo"]


def test_load_cases_rejects_followup_of_later_case(tmp_path: Path) -> None:
    followup = (
        "id: child\ntitle: Кейс\nfollowup_of: parent\nrequest:\n  user_id: u\n  client_id: c\n"
        "  role: cfo\n  action_context: {type: followup, card_id: '', question: 'Почему'}\n"
        "expect: {silent: false}\n"
    )
    write_cases(tmp_path, followup, role_case("parent", "cfo"))

    with pytest.raises(ValueError, match="child"):
        load_cases(tmp_path)


def test_role_blocks_are_card_blocks() -> None:
    assert set(ROLE_BLOCKS) <= set(CLAIM_BLOCKS)
