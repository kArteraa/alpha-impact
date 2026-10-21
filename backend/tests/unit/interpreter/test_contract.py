from apps.services.interpreter.critic import CriticAgent
from shared.config.settings import Settings
from shared.contracts.ports import Critic, Interpreter
from tests.unit.interpreter.support import make_harness


def test_agent_implements_port(settings_env: dict[str, str]) -> None:
    assert isinstance(make_harness(Settings()).agent, Interpreter)


def test_critic_implements_port(settings_env: dict[str, str]) -> None:
    critic = make_harness(Settings()).container.resolve(Critic)
    assert isinstance(critic, CriticAgent)
    assert isinstance(critic, Critic)
