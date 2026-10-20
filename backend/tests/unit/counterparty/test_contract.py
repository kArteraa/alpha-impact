import pytest

from apps.services import counterparty
from shared.contracts.ports import CounterpartyService
from shared.di.container import Container


def resolve() -> CounterpartyService:
    container = Container()
    counterparty.register(container)
    return container.resolve(CounterpartyService)


def test_implements_port() -> None:
    assert isinstance(resolve(), CounterpartyService)


async def test_methods_point_to_implementing_task() -> None:
    with pytest.raises(NotImplementedError, match="AH-8"):
        await resolve().context("client", None, None)
