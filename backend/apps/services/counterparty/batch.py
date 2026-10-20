from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.counterparty.config import CounterpartyConfig
from apps.services.counterparty.graph import build_graphs, served_clients
from apps.services.counterparty.loader import load_cards, read_payments
from apps.services.counterparty.repository import all_linked_clients, upsert_cards, upsert_graphs


async def rebuild_graph(
    sessions: async_sessionmaker[AsyncSession], raw_dir: Path, config: CounterpartyConfig
) -> int:
    cards = load_cards(raw_dir / config.companies_file, config)
    async with sessions() as session:
        linked = await all_linked_clients(session)
    clients = served_clients(cards, linked, config)
    graphs = build_graphs(read_payments(raw_dir / config.payments_file), cards, clients, config)
    async with sessions() as session, session.begin():
        await upsert_cards(session, cards)
        await upsert_graphs(session, graphs, datetime.now(UTC))
    return len(graphs)
