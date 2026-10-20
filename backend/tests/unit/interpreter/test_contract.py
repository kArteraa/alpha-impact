import pytest

from apps.services import interpreter
from shared.contracts.ports import Critic, Interpreter
from shared.contracts.schemas import InterpretRequest, PaymentContext, Role
from shared.di.container import Container


def container() -> Container:
    result = Container()
    interpreter.register(result)
    return result


def test_agent_implements_port() -> None:
    assert isinstance(container().resolve(Interpreter), Interpreter)


def test_critic_implements_port() -> None:
    assert isinstance(container().resolve(Critic), Critic)


async def test_interpret_points_to_task() -> None:
    request = InterpretRequest(
        user_id="u", client_id="c", role=Role.CFO, action_context=PaymentContext(amount=1.0)
    )
    with pytest.raises(NotImplementedError, match="AH-18"):
        await container().resolve(Interpreter).interpret(request)


async def test_review_points_to_task() -> None:
    with pytest.raises(NotImplementedError, match="AH-22"):
        await container().resolve(Critic).review(None, [], [])  # type: ignore[arg-type]
