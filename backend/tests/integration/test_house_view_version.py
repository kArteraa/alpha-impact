import re
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.house_view.batch import load_house_view
from apps.services.house_view.ingest.config import load_config
from apps.services.house_view.service import HouseView
from shared.db.models import HouseViewClaimRow
from tests.house_view_data import APPROVED, APPROVED_FILE, write_claims

TODAY = date(2026, 10, 21)
EXPIRED_DOCS = load_config().expired_docs


@pytest.fixture
async def house_view(sessions: async_sessionmaker[AsyncSession]) -> HouseView:
    await load_house_view(sessions, APPROVED_FILE, EXPIRED_DOCS)
    return HouseView(sessions, lambda: TODAY)


async def test_version_is_a_short_hex_digest(house_view: HouseView) -> None:
    assert re.fullmatch(r"[0-9a-f]{16}", await house_view.version())


async def test_reloading_same_file_keeps_version(
    house_view: HouseView, sessions: async_sessionmaker[AsyncSession]
) -> None:
    before = await house_view.version()

    await load_house_view(sessions, APPROVED_FILE, EXPIRED_DOCS)

    assert await house_view.version() == before


async def test_edited_claim_changes_version(
    house_view: HouseView, sessions: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    before = await house_view.version()
    edited = [APPROVED[0].model_copy(update={"value": "99%"}), *APPROVED[1:]]

    await load_house_view(sessions, write_claims(tmp_path / "edited.json", edited), EXPIRED_DOCS)

    assert await house_view.version() != before


async def test_removed_claim_changes_version(
    house_view: HouseView, sessions: async_sessionmaker[AsyncSession], tmp_path: Path
) -> None:
    before = await house_view.version()
    successors = {claim.superseded_by for claim in APPROVED}
    standalone = next(
        claim for claim in APPROVED if claim.superseded_by is None and claim.id not in successors
    )
    kept = [claim for claim in APPROVED if claim.id != standalone.id]

    await load_house_view(sessions, write_claims(tmp_path / "removed.json", kept), EXPIRED_DOCS)

    assert await house_view.version() != before


async def test_drafts_do_not_change_version(
    house_view: HouseView, sessions: async_sessionmaker[AsyncSession]
) -> None:
    before = await house_view.version()
    draft = APPROVED[0].model_copy(update={"id": "draft-claim", "status": "draft"})
    async with sessions() as session, session.begin():
        session.add(HouseViewClaimRow(**draft.model_dump()))

    assert await house_view.version() == before
