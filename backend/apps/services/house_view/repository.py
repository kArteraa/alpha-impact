from collections.abc import Collection, Sequence

from sqlalchemy import case, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.services.house_view.statuses import APPROVED, DRAFT, EXPIRED
from shared.contracts.schemas import HouseViewClaim
from shared.db.models import HouseViewClaimRow


async def replace_approved(
    session: AsyncSession, claims: Sequence[HouseViewClaim], expired_docs: Collection[str]
) -> None:
    machine_status = case((HouseViewClaimRow.source_doc.in_(expired_docs), EXPIRED), else_=DRAFT)
    await session.execute(
        update(HouseViewClaimRow)
        .where(
            HouseViewClaimRow.status == APPROVED,
            HouseViewClaimRow.id.not_in([claim.id for claim in claims]),
        )
        .values(status=machine_status, superseded_by=None)
    )
    if not claims:
        return
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
