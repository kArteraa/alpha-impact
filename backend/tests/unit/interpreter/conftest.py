import pytest

from shared.config.settings import Settings
from shared.contracts.schemas import HouseViewClaim
from tests.unit.interpreter.followup_support import answer_draft, deposit_trace, rate_claim
from tests.unit.interpreter.support import Harness, make_harness


@pytest.fixture
def harness(settings_env: dict[str, str]) -> Harness:
    return make_harness(Settings())


@pytest.fixture
def rate(harness: Harness) -> HouseViewClaim:
    claim = rate_claim(harness, "rate-approved")
    harness.traces.find_by_card.return_value = deposit_trace(claim)
    harness.house_view.chain.return_value = [claim]
    harness.house_view.claims.return_value = [claim]
    harness.answers[:] = [{"focus": "Ответ про ставку", "tools": []}, answer_draft(claim)]
    return claim
