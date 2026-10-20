import pytest

from apps.services import llm
from shared.contracts.ports import LLMGateway
from shared.di.container import Container


def resolve() -> LLMGateway:
    container = Container()
    llm.register(container)
    return container.resolve(LLMGateway)


def test_implements_port() -> None:
    assert isinstance(resolve(), LLMGateway)


async def test_methods_point_to_implementing_task() -> None:
    with pytest.raises(NotImplementedError, match="AH-16"):
        await resolve().budget_left_rub()
