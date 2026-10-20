from collections.abc import Iterable, Mapping
from datetime import datetime
from itertools import batched
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.services.counterparty.graph import ClientGraph
from apps.services.counterparty.loader import Card
from shared.db.models import ClientGraphRow, CounterpartyCardRow, UserClientRow
from shared.db.models.base import Base

UPSERT_BATCH = 1000


async def upsert(
    session: AsyncSession, model: type[Base], key: str, rows: Iterable[dict[str, Any]]
) -> None:
    for batch in batched(rows, UPSERT_BATCH):
        statement = insert(model).values(list(batch))
        columns = [name for name in batch[0] if name != key]
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[key],
                set_={name: statement.excluded[name] for name in columns},
                where=or_(
                    *(
                        model.__table__.c[name].is_distinct_from(statement.excluded[name])
                        for name in columns
                    )
                ),
            )
        )


async def upsert_cards(session: AsyncSession, cards: Mapping[str, Card]) -> None:
    await upsert(
        session,
        CounterpartyCardRow,
        "company_id",
        (
            {
                "company_id": company_id,
                "industry_class": card.industry_class,
                "region": card.region,
                "size_bucket": card.size_bucket,
            }
            for company_id, card in cards.items()
        ),
    )


async def upsert_graphs(
    session: AsyncSession, graphs: Mapping[str, ClientGraph], built_at: datetime
) -> None:
    await upsert(
        session,
        ClientGraphRow,
        "client_id",
        (
            {
                "client_id": client_id,
                "payload": graph.summary,
                "dependence": graph.dependence,
                "built_at": built_at,
            }
            for client_id, graph in graphs.items()
        ),
    )


async def find_card(session: AsyncSession, company_id: str) -> CounterpartyCardRow | None:
    return await session.get(CounterpartyCardRow, company_id)


async def find_flows(
    session: AsyncSession, client_id: str, beneficiary_id: str, segment: str
) -> tuple[float, float | None] | None:
    query = select(
        ClientGraphRow.payload["outflow_segments"][segment].as_float(),
        ClientGraphRow.dependence[beneficiary_id].as_float(),
    ).where(ClientGraphRow.client_id == client_id)
    row = (await session.execute(query)).one_or_none()
    if row is None:
        return None
    segment_share, dependence = row
    return segment_share or 0.0, dependence


async def all_linked_clients(session: AsyncSession) -> frozenset[str]:
    return frozenset(await session.scalars(select(UserClientRow.client_id)))
