import json
from datetime import date
from pathlib import Path

import pytest

from apps.services.house_view.approved import (
    ChainError,
    load_approved,
    validate_chains,
)
from shared.contracts.schemas import HouseViewClaim

APPROVED_FILE = Path(__file__).resolve().parents[3] / "data" / "seed" / "house_view_approved.json"
RATE_CHAIN = [date(2026, 7, 22), date(2026, 7, 31), date(2026, 9, 7), date(2026, 9, 11)]


def claim(claim_id: str, **fields: object) -> HouseViewClaim:
    base: dict[str, object] = {
        "id": claim_id,
        "claim": f"claim {claim_id}",
        "type": "forecast",
        "subject": "key_rate",
        "value": "14%",
        "date": date(2026, 7, 22),
        "valid_until": None,
        "source_doc": "report.pdf",
        "page": 1,
        "superseded_by": None,
        "status": "approved",
    }
    return HouseViewClaim.model_validate({**base, **fields})


def test_approved_file_is_valid_and_approved_only() -> None:
    claims = load_approved(APPROVED_FILE)

    assert len(claims) == len({item.id for item in claims}) >= 40
    assert {item.status for item in claims} == {"approved"}


def test_rate_forecasts_form_one_chain_and_fact_stays_outside() -> None:
    claims = {item.id: item for item in load_approved(APPROVED_FILE)}
    successors = {item.superseded_by for item in claims.values() if item.superseded_by}
    first = next(
        item
        for item in claims.values()
        if item.subject == "key_rate" and item.superseded_by and item.id not in successors
    )
    chain = [first]
    while chain[-1].superseded_by:
        chain.append(claims[chain[-1].superseded_by])

    assert [item.date for item in chain] == RATE_CHAIN
    assert {item.type for item in chain} == {"forecast"}
    fact = [item for item in claims.values() if item.subject == "key_rate" and item.type == "fact"]
    assert date(2026, 7, 24) in {item.date for item in fact}
    assert all(item.superseded_by is None and item.id not in successors for item in fact)


@pytest.mark.parametrize(
    ("successor", "reason"),
    [
        (claim("b", type="fact", date=date(2026, 8, 1)), "type"),
        (claim("b", subject="fx_rate", date=date(2026, 8, 1)), "subject"),
        (claim("b", date=date(2026, 7, 1)), "earlier"),
    ],
)
def test_chain_links_only_same_subject_type_and_forward_in_time(
    successor: HouseViewClaim, reason: str
) -> None:
    with pytest.raises(ChainError, match=reason):
        validate_chains([claim("a", superseded_by="b"), successor])


def test_chain_must_point_to_known_claim_and_have_no_cycle() -> None:
    with pytest.raises(ChainError, match="unknown"):
        validate_chains([claim("a", superseded_by="missing")])
    with pytest.raises(ChainError, match="cycle"):
        validate_chains([claim("a", superseded_by="b"), claim("b", superseded_by="a")])


def test_file_with_draft_status_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "approved.json"
    path.write_text(
        json.dumps([claim("a", status="draft").model_dump(mode="json")]), encoding="utf-8"
    )

    with pytest.raises(ChainError, match="approved"):
        load_approved(path)


def test_chain_cannot_merge_two_predecessors() -> None:
    claims = [
        claim("a", superseded_by="c"),
        claim("b", superseded_by="c"),
        claim("c", date=date(2026, 8, 1)),
    ]

    with pytest.raises(ChainError, match="more than one"):
        validate_chains(claims)
