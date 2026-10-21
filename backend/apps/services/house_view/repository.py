from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.services.house_view.approved import APPROVED
from shared.contracts.schemas import HouseViewClaim
from shared.db.models import HouseViewClaimRow


async def upsert_approved(session: AsyncSession, claims: Sequence[HouseViewClaim]) -> None:
    statement = insert(HouseViewClaimRow).values([claim.model_dump() for claim in claims])
    columns = [name for name in HouseViewClaim.model_fields if name != "id"]
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[HouseViewClaimRow.id],
            set_={name: statement.excluded[name] for name in columns},
        )
    )


async def approved_claims(session: AsyncSession, subject: str) -> Sequence[HouseViewClaimRow]:
    query = (
        select(HouseViewClaimRow)
        .where(HouseViewClaimRow.subject == subject, HouseViewClaimRow.status == APPROVED)
        .order_by(HouseViewClaimRow.date, HouseViewClaimRow.id)
    )
    return (await session.scalars(query)).all()


async def find_approved(session: AsyncSession, claim_id: str) -> HouseViewClaimRow | None:
    row = await session.get(HouseViewClaimRow, claim_id)
    return row if row is not None and row.status == APPROVED else None
