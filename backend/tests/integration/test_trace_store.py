from datetime import UTC, date, datetime

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.trace.service import TraceRepository
from shared.contracts.errors import AccessDenied, NotFound
from shared.contracts.schemas import InterpretResponse, Trace
from shared.db.models import FeedbackRow
from tests.integration.contracts.examples import CARD, REQUEST, TRACE

OWNER = REQUEST.user_id


def make_trace(trace_id: str, created_at: datetime, response: InterpretResponse) -> Trace:
    cards = [card.model_copy(update={"trace_id": trace_id}) for card in response.cards]
    return TRACE.model_copy(
        update={
            "id": trace_id,
            "created_at": created_at,
            "result": response.model_copy(update={"cards": cards}),
        }
    )


def card_response(card_id: str) -> InterpretResponse:
    return InterpretResponse(silent=False, cards=[CARD.model_copy(update={"id": card_id})])


@pytest.fixture
def store(sessions: async_sessionmaker[AsyncSession]) -> TraceRepository:
    return TraceRepository(sessions)


async def feedback_rows(sessions: async_sessionmaker[AsyncSession]) -> list[FeedbackRow]:
    async with sessions() as session:
        return list((await session.scalars(select(FeedbackRow))).all())


async def test_saved_trace_is_read_back(store: TraceRepository) -> None:
    await store.save(TRACE)
    assert await store.get(TRACE.id) == TRACE


async def test_unknown_trace_is_none(store: TraceRepository) -> None:
    assert await store.get("missing") is None


async def test_metrics_count_only_traces_of_the_period(store: TraceRepository) -> None:
    await store.save(
        make_trace("old", datetime(2026, 10, 20, 23, 59, tzinfo=UTC), card_response("c-old"))
    )
    await store.save(
        make_trace(
            "new",
            datetime(2026, 10, 21, 0, 0, tzinfo=UTC),
            InterpretResponse(silent=True, silent_reason="Нет событий"),
        )
    )
    recent = await store.metrics(date(2026, 10, 21))
    assert recent["silent_share"] == 1.0
    assert "tokens_per_card" not in recent
    whole = await store.metrics(date(2026, 10, 20))
    assert (whole["silent_share"], whole["tokens_per_card"]) == (0.5, 160.0)


async def test_feedback_is_recorded_against_card_trace(
    store: TraceRepository, sessions: async_sessionmaker[AsyncSession]
) -> None:
    await store.save(make_trace("t-1", TRACE.created_at, card_response("card-a")))
    await store.save(make_trace("t-2", TRACE.created_at, card_response("card-b")))
    await store.feedback(OWNER, "card-b", True, "Полезно")
    rows = await feedback_rows(sessions)
    assert [(row.card_id, row.trace_id, row.useful, row.comment) for row in rows] == [
        ("card-b", "t-2", True, "Полезно")
    ]


async def test_repeated_feedback_replaces_previous(
    store: TraceRepository, sessions: async_sessionmaker[AsyncSession]
) -> None:
    await store.save(make_trace("t-1", TRACE.created_at, card_response("card-a")))
    await store.feedback(OWNER, "card-a", True, "Полезно")
    await store.feedback(OWNER, "card-a", False, None)
    rows = await feedback_rows(sessions)
    assert [(row.card_id, row.useful, row.comment) for row in rows] == [("card-a", False, None)]


async def test_feedback_on_foreign_card_is_denied(
    store: TraceRepository, sessions: async_sessionmaker[AsyncSession]
) -> None:
    await store.save(make_trace("t-1", TRACE.created_at, card_response("card-a")))
    with pytest.raises(AccessDenied):
        await store.feedback("someone-else", "card-a", True, None)
    assert await feedback_rows(sessions) == []


async def test_feedback_on_unknown_card_is_not_found(store: TraceRepository) -> None:
    await store.save(make_trace("t-1", TRACE.created_at, card_response("card-a")))
    with pytest.raises(NotFound):
        await store.feedback(OWNER, "card-z", True, None)


async def test_card_lookup_uses_payload_index(sessions: async_sessionmaker[AsyncSession]) -> None:
    async with sessions() as session:
        definition = await session.scalar(
            text("SELECT indexdef FROM pg_indexes WHERE indexname = 'ix_traces_payload'")
        )
    assert definition is not None
    assert "gin" in definition.lower()
    assert "jsonb_path_ops" in definition


async def test_find_by_card_returns_card_trace(store: TraceRepository) -> None:
    await store.save(make_trace("t-1", TRACE.created_at, card_response("card-a")))
    expected = make_trace("t-2", TRACE.created_at, card_response("card-b"))
    await store.save(expected)
    found = await store.find_by_card(user_id=OWNER, client_id=REQUEST.client_id, card_id="card-b")
    assert found == expected


async def test_find_by_card_unknown_card_is_not_found(store: TraceRepository) -> None:
    await store.save(make_trace("t-1", TRACE.created_at, card_response("card-a")))
    with pytest.raises(NotFound):
        await store.find_by_card(user_id=OWNER, client_id=REQUEST.client_id, card_id="card-z")


@pytest.mark.parametrize(
    ("user_id", "client_id"),
    [("someone-else", REQUEST.client_id), (OWNER, "another-client")],
)
async def test_find_by_card_of_foreign_trace_is_denied(
    store: TraceRepository, user_id: str, client_id: str
) -> None:
    await store.save(make_trace("t-1", TRACE.created_at, card_response("card-a")))
    with pytest.raises(AccessDenied):
        await store.find_by_card(user_id=user_id, client_id=client_id, card_id="card-a")
