from unittest.mock import AsyncMock

import pytest

from apps.services.gateway.calls import CallRecord
from apps.services.gateway.service import InterpretGateway
from shared.contracts.errors import AccessDenied, BudgetExceeded, DomainError
from shared.contracts.schemas import (
    Claim,
    ClaimType,
    ClientProfile,
    InsightCard,
    InterpretRequest,
    InterpretResponse,
    PaymentContext,
    Role,
    SourceRef,
)

USER = "user"
CLIENT = "U_1"


class MemoryCache:
    def __init__(self) -> None:
        self.entries: dict[str, InterpretResponse] = {}

    async def get(self, key: str) -> InterpretResponse | None:
        return self.entries.get(key)

    async def put(self, key: str, response: InterpretResponse) -> None:
        self.entries[key] = response


class MemoryJournal:
    def __init__(self) -> None:
        self.records: list[CallRecord] = []
        self.broken = False

    async def record(self, call: CallRecord) -> None:
        if self.broken:
            raise RuntimeError("journal is down")
        self.records.append(call)


class Profiles:
    def __init__(self) -> None:
        self.version = 1
        self.calls: list[tuple[str, str]] = []

    async def get_profile(self, user_id: str, client_id: str) -> ClientProfile:
        self.calls.append((user_id, client_id))
        if client_id != CLIENT:
            raise AccessDenied(f"User {user_id} has no access to client {client_id}")
        return ClientProfile(
            client_id=client_id,
            group_id=None,
            group_members=[],
            features={},
            exposures={},
            flags={},
            version=self.version,
        )


def card() -> InsightCard:
    claim = Claim(
        text="Ставка снижена",
        type=ClaimType.FACT,
        source_ref=SourceRef(kind="news", id="n1"),
    )
    return InsightCard(
        id="c1",
        headline="Ставка",
        what_happened=[claim],
        why_for_you=[claim],
        consequences=[claim],
        actions=[claim],
        bank_view=[],
        basis=[claim.source_ref],
        significance=0.5,
        trace_id="trace-1",
    )


def request(client_id: str = CLIENT, user_id: str = USER) -> InterpretRequest:
    return InterpretRequest(
        user_id=user_id,
        client_id=client_id,
        role=Role.CFO,
        action_context=PaymentContext(beneficiary_id="B_1", amount=100.0),
    )


class Harness:
    def __init__(self) -> None:
        self.interpreter = AsyncMock()
        self.interpreter.interpret.return_value = InterpretResponse(silent=False, cards=[card()])
        self.house_view = AsyncMock()
        self.house_view.version.return_value = "v1"
        self.profiles = Profiles()
        self.cache = MemoryCache()
        self.journal = MemoryJournal()
        self.gateway = InterpretGateway(
            interpreter=self.interpreter,
            house_view=self.house_view,
            profiles=self.profiles,
            cache=self.cache,
            journal=self.journal,
        )


@pytest.fixture
def harness() -> Harness:
    return Harness()


async def test_foreign_client_is_denied_before_interpreter(harness: Harness) -> None:
    with pytest.raises(AccessDenied):
        await harness.gateway.interpret(USER, request(client_id="U_9"))
    harness.interpreter.interpret.assert_not_awaited()
    assert harness.profiles.calls == [(USER, "U_9")]
    assert harness.journal.records == []


async def test_request_for_another_user_is_denied(harness: Harness) -> None:
    with pytest.raises(AccessDenied):
        await harness.gateway.interpret(USER, request(user_id="someone"))
    harness.interpreter.interpret.assert_not_awaited()


async def test_repeated_request_is_served_from_cache(harness: Harness) -> None:
    first = await harness.gateway.interpret(USER, request())
    second = await harness.gateway.interpret(USER, request())
    assert first.cached is False
    assert second.cached is True
    assert second.cards == first.cards
    harness.interpreter.interpret.assert_awaited_once()


async def test_new_house_view_version_misses_cache(harness: Harness) -> None:
    await harness.gateway.interpret(USER, request())
    harness.house_view.version.return_value = "v2"
    response = await harness.gateway.interpret(USER, request())
    assert response.cached is False
    assert harness.interpreter.interpret.await_count == 2


async def test_journal_records_each_call(harness: Harness) -> None:
    await harness.gateway.interpret(USER, request())
    await harness.gateway.interpret(USER, request())
    first, second = harness.journal.records
    assert (first.user_id, first.client_id, first.action_type) == (USER, CLIENT, "payment")
    assert (first.trace_id, first.cached, first.outcome) == ("trace-1", False, "ok")
    assert (second.cached, second.outcome) == (True, "ok")
    assert first.context_hash == second.context_hash
    assert first.duration_ms >= 0


async def test_silent_response_has_no_trace_id(harness: Harness) -> None:
    harness.interpreter.interpret.return_value = InterpretResponse(silent=True, silent_reason="x")
    response = await harness.gateway.interpret(USER, request())
    assert response.silent
    assert harness.journal.records[0].trace_id is None


async def test_interpreter_error_is_journaled_and_not_cached(harness: Harness) -> None:
    harness.interpreter.interpret.side_effect = DomainError("bad draft")
    with pytest.raises(DomainError):
        await harness.gateway.interpret(USER, request())
    assert harness.cache.entries == {}
    assert harness.journal.records[0].outcome == "DomainError"
    assert harness.journal.records[0].cached is False


async def test_profile_correction_misses_cache(harness: Harness) -> None:
    await harness.gateway.interpret(USER, request())
    harness.profiles.version = 2
    response = await harness.gateway.interpret(USER, request())
    assert response.cached is False
    assert harness.interpreter.interpret.await_count == 2


async def test_cache_is_not_shared_between_users(harness: Harness) -> None:
    await harness.gateway.interpret(USER, request())
    response = await harness.gateway.interpret("colleague", request(user_id="colleague"))
    assert response.cached is False
    assert harness.interpreter.interpret.await_count == 2


async def test_broken_journal_does_not_break_response(harness: Harness) -> None:
    harness.journal.broken = True
    response = await harness.gateway.interpret(USER, request())
    assert response.cards == [card()]
    assert len(harness.cache.entries) == 1


async def test_broken_journal_keeps_original_error(harness: Harness) -> None:
    harness.journal.broken = True
    harness.interpreter.interpret.side_effect = BudgetExceeded("no budget")
    with pytest.raises(BudgetExceeded):
        await harness.gateway.interpret(USER, request())
