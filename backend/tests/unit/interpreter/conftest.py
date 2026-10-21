import pytest

from shared.config.settings import Settings
from tests.unit.interpreter.support import Harness, make_harness


@pytest.fixture
def harness(settings_env: dict[str, str]) -> Harness:
    return make_harness(Settings())
