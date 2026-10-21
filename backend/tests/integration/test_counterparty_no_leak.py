import json
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.counterparty.batch import rebuild_graph
from apps.services.counterparty.config import load_config
from apps.services.counterparty.service import CounterpartyAggregates
from scripts.seed import RAW_DIR, seed_users
from shared.contracts.schemas import CounterpartyContext
from shared.db.models import ClientGraphRow, CounterpartyCardRow
from tests.leak import PAYMENTS_FILE, assert_no_foreign_data, load_foreign_data, seed_clients
from tests.unit.counterparty.fixtures import AMOUNTS, CLIENT, FIXTURES_DIR

CONFIG = load_config()
LOW = CONFIG.confidence.low
UNKNOWN_COMPANY = "U_999999999"
UNKNOWN_INN = "7707083893"
AGGREGATE_FIELDS = {
    "industry_class",
    "region",
    "size_bucket",
    "share_of_client_outflow",
    "share_of_counterparty_inflow",
    "confidence",
}
STALE = "U_800"
STALE_CARD = {
    "company_id": STALE,
    "industry_class": "logistics",
    "region": "Москва",
    "size_bucket": "small",
}
STALE_GRAPH = {
    "client_id": STALE,
    "payload": {"outflow_segments": {}},
    "dependence": {},
    "built_at": datetime(2026, 1, 1, tzinfo=UTC),
}


@pytest.fixture
async def service(sessions: async_sessionmaker[AsyncSession]) -> CounterpartyAggregates:
    await rebuild_graph(sessions, FIXTURES_DIR, CONFIG)
    return CounterpartyAggregates(sessions, CONFIG)


async def table_sizes(sessions: async_sessionmaker[AsyncSession]) -> tuple[int, int]:
    async with sessions() as session:
        cards = await session.scalar(select(func.count()).select_from(CounterpartyCardRow))
        graphs = await session.scalar(select(func.count()).select_from(ClientGraphRow))
    return cards or 0, graphs or 0


async def graph_built_at(sessions: async_sessionmaker[AsyncSession]) -> datetime | None:
    async with sessions() as session:
        return await session.scalar(select(ClientGraphRow.built_at))


def assert_no_leak(context: CounterpartyContext) -> None:
    dumped = context.model_dump(mode="json")
    text = json.dumps(dumped, ensure_ascii=False)
    assert set(dumped) == set(CounterpartyContext.model_fields)
    assert "U_" not in text
    for amount in AMOUNTS:
        assert str(int(amount)) not in text
    for share in (context.share_of_client_outflow, context.share_of_counterparty_inflow):
        assert share is None or 0 <= share <= 1


async def test_paid_logistics_carrier_returns_only_aggregates(
    service: CounterpartyAggregates,
) -> None:
    context = await service.context(CLIENT, "U_902", None)

    assert context == CounterpartyContext(
        industry_class="logistics",
        region="Санкт-Петербург",
        size_bucket="small",
        share_of_client_outflow=0.4,
        share_of_counterparty_inflow=0.75,
        confidence=CONFIG.confidence.linked,
    )
    assert_no_leak(context)


async def test_counterparty_without_card_has_low_confidence(
    service: CounterpartyAggregates,
) -> None:
    context = await service.context(CLIENT, "U_950", None)

    assert context.industry_class is None
    assert context.region is None
    assert context.size_bucket is None
    assert context.share_of_client_outflow == 0.4
    assert context.share_of_counterparty_inflow == 1.0
    assert context.confidence == LOW
    assert_no_leak(context)


async def test_card_without_payments_has_medium_confidence(
    service: CounterpartyAggregates,
) -> None:
    context = await service.context(CLIENT, "U_905", None)

    assert context.industry_class == "retail"
    assert context.size_bucket == "medium"
    assert context.share_of_client_outflow == 0.0
    assert context.share_of_counterparty_inflow is None
    assert context.confidence == CONFIG.confidence.card_only
    assert_no_leak(context)


@pytest.mark.parametrize(
    ("beneficiary_id", "inn"),
    [(None, "7707083893"), (None, None), ("U_999", None), (CLIENT, None)],
)
async def test_unknown_counterparty_returns_nothing_but_low_confidence(
    service: CounterpartyAggregates, beneficiary_id: str | None, inn: str | None
) -> None:
    context = await service.context(CLIENT, beneficiary_id, inn)

    assert context.industry_class is None
    assert context.share_of_client_outflow is None
    assert context.share_of_counterparty_inflow is None
    assert context.confidence == LOW
    assert_no_leak(context)


async def test_client_without_graph_still_gets_card_aggregates(
    service: CounterpartyAggregates,
) -> None:
    context = await service.context("U_904", "U_902", None)

    assert context.industry_class == "logistics"
    assert context.share_of_client_outflow is None
    assert context.share_of_counterparty_inflow is None
    assert context.confidence == CONFIG.confidence.card_only


async def test_rebuild_is_idempotent(
    service: CounterpartyAggregates, sessions: async_sessionmaker[AsyncSession]
) -> None:
    before = await service.context(CLIENT, "U_902", None)
    built_at = await graph_built_at(sessions)
    await rebuild_graph(sessions, FIXTURES_DIR, CONFIG)

    assert await table_sizes(sessions) == (5, 1)
    assert await service.context(CLIENT, "U_902", None) == before
    assert await graph_built_at(sessions) == built_at


async def test_rebuild_drops_rows_missing_from_data(
    service: CounterpartyAggregates, sessions: async_sessionmaker[AsyncSession]
) -> None:
    async with sessions() as session, session.begin():
        session.add(CounterpartyCardRow(**STALE_CARD))
        session.add(ClientGraphRow(**STALE_GRAPH))
    await rebuild_graph(sessions, FIXTURES_DIR, CONFIG)

    assert await table_sizes(sessions) == (5, 1)
    assert (await service.context(CLIENT, STALE, None)).confidence == LOW
    assert (await service.context(STALE, "U_902", None)).share_of_client_outflow is None


@pytest.mark.skipif(not PAYMENTS_FILE.exists(), reason="data/raw is not present")
async def test_seed_clients_see_only_aggregates_of_their_recipients(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    await seed_users(sessions)
    await rebuild_graph(sessions, RAW_DIR, CONFIG)
    service = CounterpartyAggregates(sessions, CONFIG)

    for client_id, foreign in load_foreign_data(seed_clients()).items():
        assert foreign.recipients
        for beneficiary_id, inn in [
            *((recipient, None) for recipient in sorted(foreign.recipients)),
            (UNKNOWN_COMPANY, None),
            (None, UNKNOWN_INN),
        ]:
            context = await service.context(client_id, beneficiary_id, inn)
            assert set(context.model_dump()) == AGGREGATE_FIELDS
            assert_no_foreign_data(context, client_id, foreign)
