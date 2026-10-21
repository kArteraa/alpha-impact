import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.counterparty.batch import rebuild_graph
from apps.services.profile.batch import rebuild_profiles
from apps.services.profile.config import load_config as load_profile_config
from main import build_container
from scripts.seed import RAW_DIR, seed_users
from shared.contracts.ports import CounterpartyService, ProductRulesService, ProfileService
from shared.contracts.schemas import InsightCard, InterpretRequest, PaymentContext, Role
from tests.leak import (
    CONFIG,
    PAYMENTS_FILE,
    assert_no_foreign_data,
    probes,
    seed_clients,
    seed_foreign_data,
)
from tests.mocks.interpreter import MockInterpreter

PAYMENT_AMOUNT = 1_500_000.0


def sourced(card: InsightCard) -> bool:
    claims = [
        *card.what_happened,
        *card.why_for_you,
        *card.consequences,
        *card.actions,
        *card.bank_view,
    ]
    return bool(claims) and all(claim.source_ref in card.basis for claim in claims)


@pytest.mark.skipif(not PAYMENTS_FILE.exists(), reason="data/raw is not present")
async def test_seed_cards_contain_no_foreign_data(
    sessions: async_sessionmaker[AsyncSession],
) -> None:
    await seed_users(sessions)
    await rebuild_profiles(sessions, RAW_DIR, load_profile_config())
    await rebuild_graph(sessions, RAW_DIR, CONFIG)
    container = build_container()
    interpreter = MockInterpreter(
        container.resolve(CounterpartyService),
        container.resolve(ProfileService),
        container.resolve(ProductRulesService),
    )
    users = seed_clients()

    try:
        for client_id, foreign in seed_foreign_data().items():
            for beneficiary_id, inn in probes(foreign):
                request = InterpretRequest(
                    user_id=users[client_id],
                    client_id=client_id,
                    role=Role.CFO,
                    action_context=PaymentContext(
                        beneficiary_id=beneficiary_id, inn=inn, amount=PAYMENT_AMOUNT
                    ),
                )
                response = await interpreter.interpret(request)
                assert response.silent != bool(response.cards)
                assert all(sourced(card) for card in response.cards)
                assert_no_foreign_data(response, client_id, foreign)
    finally:
        await container.aclose()
