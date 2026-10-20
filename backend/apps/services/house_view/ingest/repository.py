from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from shared.contracts.schemas import HouseViewClaim
from shared.db.models import HouseViewClaimRow, ReportPageRow


async def cached_text(
    session: AsyncSession, source_doc: str, page: int, image_sha256: str
) -> str | None:
    row = await session.get(ReportPageRow, (source_doc, page))
    return row.text if row is not None and row.image_sha256 == image_sha256 else None


async def save_page(
    session: AsyncSession, source_doc: str, page: int, image_sha256: str, text: str
) -> None:
    statement = insert(ReportPageRow).values(
        source_doc=source_doc, page=page, image_sha256=image_sha256, text=text
    )
    await session.execute(
        statement.on_conflict_do_update(
            index_elements=[ReportPageRow.source_doc, ReportPageRow.page],
            set_={"image_sha256": statement.excluded.image_sha256, "text": statement.excluded.text},
        )
    )


async def document_pages(session: AsyncSession, source_doc: str) -> list[ReportPageRow]:
    query = (
        select(ReportPageRow)
        .where(ReportPageRow.source_doc == source_doc)
        .order_by(ReportPageRow.page)
    )
    return list(await session.scalars(query))


async def add_claims(session: AsyncSession, claims: list[HouseViewClaim]) -> None:
    if claims:
        statement = insert(HouseViewClaimRow).values([claim.model_dump() for claim in claims])
        await session.execute(
            statement.on_conflict_do_nothing(index_elements=[HouseViewClaimRow.id])
        )


async def claim_count(session: AsyncSession) -> int:
    return int(await session.scalar(select(func.count()).select_from(HouseViewClaimRow)) or 0)
