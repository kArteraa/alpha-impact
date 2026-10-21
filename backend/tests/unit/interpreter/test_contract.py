import pytest

from apps.services import interpreter
from shared.config.settings import Settings
from shared.contracts.ports import Critic, Interpreter
from shared.di.container import Container
from tests.unit.interpreter.support import make_harness


def container() -> Container:
    result = Container()
    interpreter.register(result)
    return result


def test_agent_implements_port(settings_env: dict[str, str]) -> None:
    assert isinstance(make_harness(Settings()).agent, Interpreter)


def test_critic_implements_port() -> None:
    assert isinstance(container().resolve(Critic), Critic)


async def test_review_points_to_task() -> None:
    with pytest.raises(NotImplementedError, match="AH-22"):
        await container().resolve(Critic).review(None, [], [])  # type: ignore[arg-type]
