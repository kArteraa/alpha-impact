from collections.abc import Mapping
from datetime import datetime
from itertools import batched

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from apps.services.counterparty.graph import Payload
from apps.services.counterparty.loader import Card
from shared.db.models import ClientGraphRow, CounterpartyCardRow, UserClientRow

UPSERT_BATCH = 1000


async def upsert_cards(session: AsyncSession, cards: Mapping[str, Card]) -> None:
    rows = [
        {
            "company_id": company_id,
            "industry_class": card.industry_class,
            "region": card.region,
            "size_bucket": card.size_bucket,
        }
        for company_id, card in cards.items()
    ]
    for batch in batched(rows, UPSERT_BATCH):
        statement = insert(CounterpartyCardRow).values(list(batch))
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[CounterpartyCardRow.company_id],
                set_={
                    "industry_class": statement.excluded.industry_class,
                    "region": statement.excluded.region,
                    "size_bucket": statement.excluded.size_bucket,
                },
            )
        )


async def upsert_graphs(
    session: AsyncSession, graphs: Mapping[str, Payload], built_at: datetime
) -> None:
    rows = [
        {"client_id": client_id, "payload": payload, "built_at": built_at}
        for client_id, payload in graphs.items()
    ]
    for batch in batched(rows, UPSERT_BATCH):
        statement = insert(ClientGraphRow).values(list(batch))
        await session.execute(
            statement.on_conflict_do_update(
                index_elements=[ClientGraphRow.client_id],
                set_={
                    "payload": statement.excluded.payload,
                    "built_at": statement.excluded.built_at,
                },
                where=ClientGraphRow.payload.is_distinct_from(statement.excluded.payload),
            )
        )


async def find_card(session: AsyncSession, company_id: str) -> CounterpartyCardRow | None:
    return await session.get(CounterpartyCardRow, company_id)


async def find_graph(session: AsyncSession, client_id: str) -> ClientGraphRow | None:
    return await session.get(ClientGraphRow, client_id)


async def all_linked_clients(session: AsyncSession) -> frozenset[str]:
    return frozenset(await session.scalars(select(UserClientRow.client_id)))
