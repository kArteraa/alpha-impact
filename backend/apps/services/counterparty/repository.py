from collections.abc import Mapping, Sequence
from datetime import datetime
from itertools import batched
from typing import Any

from sqlalchemy import String, all_, bindparam, delete, or_, select, true
from sqlalchemy.dialects.postgresql import ARRAY, insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from apps.services.counterparty.graph import ClientGraph
from apps.services.counterparty.loader import Card
from shared.db.models import ClientGraphRow, CounterpartyCardRow, UserClientRow
from shared.db.models.base import Base

UPSERT_BATCH = 1000

Found = tuple[CounterpartyCardRow | None, dict[str, float] | None, float | None]


async def replace(
    session: AsyncSession,
    model: type[Base],
    key: str,
    rows: Mapping[str, dict[str, Any]],
    stamps: Sequence[str],
) -> None:
    table = model.__table__
    kept = bindparam("kept", list(rows), type_=ARRAY(String))
    await session.execute(delete(model).where(table.c[key] != all_(kept)))
    for batch in batched(({key: row_key, **row} for row_key, row in rows.items()), UPSERT_BATCH):
        statement = insert(model).values(list(batch))
        columns = [name for name in batch[0] if name != key]
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[key],
                set_={name: statement.excluded[name] for name in columns},
                where=or_(
                    *(
                        table.c[name].is_distinct_from(statement.excluded[name])
                        for name in columns
                        if name not in stamps
                    )
                ),
            )
        )


async def replace_cards(session: AsyncSession, cards: Mapping[str, Card]) -> None:
    await replace(
        session,
        CounterpartyCardRow,
        "company_id",
        {
            company_id: {
                "industry_class": card.industry_class,
                "region": card.region,
                "size_bucket": card.size_bucket,
            }
            for company_id, card in cards.items()
        },
        (),
    )


async def replace_graphs(
    session: AsyncSession, graphs: Mapping[str, ClientGraph], built_at: datetime
) -> None:
    await replace(
        session,
        ClientGraphRow,
        "client_id",
        {
            client_id: {
                "payload": graph.summary,
                "dependence": graph.dependence,
                "built_at": built_at,
            }
            for client_id, graph in graphs.items()
        },
        ("built_at",),
    )


async def find_counterparty(
    session: AsyncSession, client_id: str, beneficiary_id: str
) -> Found | None:
    cards = (
        select(CounterpartyCardRow)
        .where(CounterpartyCardRow.company_id == beneficiary_id)
        .subquery()
    )
    graphs = (
        select(
            ClientGraphRow.payload["outflow_segments"].label("segments"),
            ClientGraphRow.dependence[beneficiary_id].as_float().label("dependence"),
        )
        .where(ClientGraphRow.client_id == client_id)
        .subquery()
    )
    query = select(
        aliased(CounterpartyCardRow, cards), graphs.c.segments, graphs.c.dependence
    ).select_from(cards.join(graphs, true(), full=True))
    row = (await session.execute(query)).one_or_none()
    found: Found | None = (row[0], row[1], row[2]) if row else None
    return found


async def all_linked_clients(session: AsyncSession) -> frozenset[str]:
    return frozenset(await session.scalars(select(UserClientRow.client_id)))
