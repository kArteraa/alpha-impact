import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.house_view.repository import all_approved, approved_claims, find_approved
from apps.services.house_view.statuses import APPROVED, EXPIRED, SUPERSEDED
from shared.contracts.errors import NotFound
from shared.contracts.schemas import HouseViewClaim
from shared.db.models import HouseViewClaimRow

VERSION_LENGTH = 16


def as_claim(row: HouseViewClaimRow, status: str) -> HouseViewClaim:
    claim = HouseViewClaim.model_validate(row, from_attributes=True)
    return claim.model_copy(update={"status": status})


def status_on(row: HouseViewClaimRow, by_id: Mapping[str, HouseViewClaimRow], day: date) -> str:
    successor = by_id.get(row.superseded_by) if row.superseded_by else None
    if successor is not None and successor.date <= day:
        return SUPERSEDED
    if row.valid_until is not None and row.valid_until < day:
        return EXPIRED
    return APPROVED


def ordered_chain(
    start: HouseViewClaimRow, rows: Sequence[HouseViewClaimRow]
) -> list[HouseViewClaimRow]:
    by_id = {row.id: row for row in rows}
    predecessor = {row.superseded_by: row for row in rows if row.superseded_by}
    head = start
    while head.id in predecessor:
        head = predecessor[head.id]
    chain = [head]
    while (successor := chain[-1].superseded_by) is not None and successor in by_id:
        chain.append(by_id[successor])
    return chain


class HouseView:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], today: Callable[[], date]
    ) -> None:
        self._sessions = sessions
        self._today = today

    async def claims(self, subject: str, as_of: date) -> list[HouseViewClaim]:
        async with self._sessions() as session:
            rows = await approved_claims(session, subject)
        by_id = {row.id: row for row in rows}
        return [as_claim(row, status_on(row, by_id, as_of)) for row in rows if row.date <= as_of]

    async def chain(self, claim_id: str) -> list[HouseViewClaim]:
        async with self._sessions() as session:
            start = await find_approved(session, claim_id)
            if start is None:
                raise NotFound(f"Approved house view claim {claim_id} not found")
            rows = await approved_claims(session, start.subject)
        by_id = {row.id: row for row in rows}
        day = self._today()
        return [as_claim(row, status_on(row, by_id, day)) for row in ordered_chain(start, rows)]

    async def version(self) -> str:
        async with self._sessions() as session:
            rows = await all_approved(session)
        snapshot = [
            HouseViewClaim.model_validate(row, from_attributes=True).model_dump(mode="json")
            for row in rows
        ]
        digest = hashlib.sha256(json.dumps(snapshot, ensure_ascii=False, sort_keys=True).encode())
        return digest.hexdigest()[:VERSION_LENGTH]
