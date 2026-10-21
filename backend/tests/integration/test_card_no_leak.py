import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.counterparty.batch import rebuild_graph
from apps.services.counterparty.config import load_config as load_counterparty_config
from apps.services.profile.batch import rebuild_profiles
from apps.services.profile.config import load_config as load_profile_config
from main import build_container
from scripts.seed import RAW_DIR, seed_users
from shared.contracts.ports import (
    CounterpartyService,
    Interpreter,
    ProductRulesService,
    ProfileService,
)
from shared.contracts.schemas import InsightCard, InterpretRequest, PaymentContext, Role
from tests.leak import PAYMENTS_FILE, assert_no_foreign_data, load_foreign_data, seed_clients
from tests.mocks.interpreter import MockInterpreter

PAYMENT_AMOUNT = 1_500_000.0
UNKNOWN_COMPANY = "U_999999999"
UNKNOWN_INN = "7707083893"


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
    await rebuild_graph(sessions, RAW_DIR, load_counterparty_config())
    container = build_container()
    container.register(
        Interpreter,
        lambda c: MockInterpreter(
            c.resolve(CounterpartyService), c.resolve(ProfileService), c.resolve(ProductRulesService)
        ),
    )
    interpreter = container.resolve(Interpreter)
    users = seed_clients()

    try:
        for client_id, foreign in load_foreign_data(users).items():
            for beneficiary_id, inn in [
                *((recipient, None) for recipient in sorted(foreign.recipients)),
                (UNKNOWN_COMPANY, None),
                (None, UNKNOWN_INN),
            ]:
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
