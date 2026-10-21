import json
from datetime import date, timedelta
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.house_view.approved import load_approved
from apps.services.house_view.batch import load_house_view
from apps.services.house_view.service import HouseView
from shared.contracts.errors import NotFound
from shared.contracts.schemas import HouseViewClaim
from shared.db.models import HouseViewClaimRow

APPROVED_FILE = Path(__file__).resolve().parents[2] / "data" / "seed" / "house_view_approved.json"
APPROVED = load_approved(APPROVED_FILE)
SUBJECTS = sorted({claim.subject for claim in APPROVED})
DRAFT = HouseViewClaim(
    id="draft-key-rate",
    claim="Черновик про ставку",
    type="forecast",
    subject="key_rate",
    value="10%",
    date=date(2026, 7, 1),
    valid_until=None,
    source_doc="report.pdf",
    page=1,
    superseded_by=None,
    status="draft",
)
EXPIRED_DOC = "steel.pdf"
TODAY = date(2026, 9, 15)


@pytest.fixture
async def house_view(sessions: async_sessionmaker[AsyncSession]) -> HouseView:
    async with sessions() as session, session.begin():
        session.add(HouseViewClaimRow(**DRAFT.model_dump()))
    await load_house_view(sessions, APPROVED_FILE, {EXPIRED_DOC})
    return HouseView(sessions, lambda: TODAY)


def current(claims: list[HouseViewClaim]) -> set[tuple[date, str, str | None]]:
    return {(item.date, item.type, item.value) for item in claims if item.status == "approved"}


async def test_rate_on_first_of_august(house_view: HouseView) -> None:
    claims = await house_view.claims("key_rate", date(2026, 8, 1))

    assert current(claims) == {
        (date(2026, 7, 24), "fact", "14,0%"),
        (date(2026, 7, 31), "forecast", "13,5%"),
    }
    assert {item.date for item in claims if item.status == "superseded"} == {date(2026, 7, 22)}


async def test_rate_on_fifteenth_of_september_differs(house_view: HouseView) -> None:
    august = current(await house_view.claims("key_rate", date(2026, 8, 1)))
    september = await house_view.claims("key_rate", date(2026, 9, 15))

    assert current(september) == {
        (date(2026, 7, 24), "fact", "14,0%"),
        (date(2026, 9, 11), "fact", "14,0%"),
        (date(2026, 9, 11), "forecast", "14,0%"),
        (date(2026, 9, 11), "forecast", "12,0%"),
    }
    assert current(september) != august
    superseded = {item.date for item in september if item.status == "superseded"}
    assert superseded == {date(2026, 7, 22), date(2026, 7, 31), date(2026, 9, 7)}


async def test_superseded_claim_is_never_approved(house_view: HouseView) -> None:
    successors = {claim.id: claim for claim in APPROVED}
    day = date(2026, 7, 1)
    while day <= date(2026, 12, 31):
        for subject in SUBJECTS:
            for item in await house_view.claims(subject, day):
                successor = successors[item.id].superseded_by
                if successor and successors[successor].date <= day:
                    assert item.status == "superseded"
                assert item.date <= day
        day += timedelta(days=7)


async def test_claims_after_valid_until_are_expired(house_view: HouseView) -> None:
    claims = await house_view.claims("gold", date(2026, 9, 15))

    assert {item.status for item in claims} == {"expired"}


async def test_drafts_are_never_returned(house_view: HouseView) -> None:
    claims = await house_view.claims("key_rate", date(2026, 12, 31))

    assert DRAFT.id not in {item.id for item in claims}


async def test_chain_runs_from_first_forecast_to_last(house_view: HouseView) -> None:
    middle = next(
        item for item in APPROVED if item.subject == "key_rate" and item.date == date(2026, 9, 7)
    )

    chain = await house_view.chain(middle.id)

    assert [item.date for item in chain] == [
        date(2026, 7, 22),
        date(2026, 7, 31),
        date(2026, 9, 7),
        date(2026, 9, 11),
    ]
    assert [item.status for item in chain] == ["superseded", "superseded", "superseded", "approved"]


async def test_chain_marks_last_forecast_expired_after_valid_until(
    sessions: async_sessionmaker[AsyncSession], house_view: HouseView
) -> None:
    last = next(
        item for item in APPROVED if item.subject == "key_rate" and item.date == date(2026, 9, 11)
    )
    later = HouseView(sessions, lambda: date(2027, 1, 10))

    chain = await later.chain(last.id)

    assert chain[-1].valid_until is not None and chain[-1].valid_until < date(2027, 1, 10)
    assert chain[-1].status == "expired"


async def test_unknown_claim_is_not_found(house_view: HouseView) -> None:
    with pytest.raises(NotFound):
        await house_view.chain("missing")
    with pytest.raises(NotFound):
        await house_view.chain(DRAFT.id)


async def test_reload_adds_no_duplicates(
    house_view: HouseView, sessions: async_sessionmaker[AsyncSession]
) -> None:
    await load_house_view(sessions, APPROVED_FILE, {EXPIRED_DOC})

    async with sessions() as session:
        count = await session.scalar(select(func.count()).select_from(HouseViewClaimRow))
    assert count == len(APPROVED) + 1


async def test_claim_removed_from_file_is_no_longer_approved(
    house_view: HouseView, sessions: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    kept = [claim for claim in APPROVED if claim.subject != "gold"]
    path = tmp_path / "approved.json"
    path.write_text(
        json.dumps([claim.model_dump(mode="json") for claim in kept], ensure_ascii=False),
        encoding="utf-8",
    )

    await load_house_view(sessions, path, {EXPIRED_DOC})

    assert await house_view.claims("gold", date(2026, 8, 15)) == []
    async with sessions() as session:
        gold = await session.scalar(
            select(HouseViewClaimRow.status).where(HouseViewClaimRow.subject == "gold")
        )
    assert gold == "draft"


async def test_empty_file_demotes_every_approved_claim(
    house_view: HouseView, sessions: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    path = tmp_path / "approved.json"
    path.write_text("[]", encoding="utf-8")

    assert await load_house_view(sessions, path, {EXPIRED_DOC}) == 0
    assert await house_view.claims("key_rate", date(2026, 9, 15)) == []


async def test_claim_from_expired_document_goes_back_as_expired(
    house_view: HouseView, sessions: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    steel = DRAFT.model_copy(
        update={"id": "steel", "source_doc": EXPIRED_DOC, "status": "approved"}
    )
    path = tmp_path / "approved.json"
    path.write_text(json.dumps([steel.model_dump(mode="json")]), encoding="utf-8")
    await load_house_view(sessions, path, {EXPIRED_DOC})
    path.write_text("[]", encoding="utf-8")

    await load_house_view(sessions, path, {EXPIRED_DOC})

    async with sessions() as session:
        status = await session.scalar(
            select(HouseViewClaimRow.status).where(HouseViewClaimRow.id == steel.id)
        )
    assert status == "expired"
