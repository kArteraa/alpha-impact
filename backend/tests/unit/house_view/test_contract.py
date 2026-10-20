import pytest

from apps.services import house_view
from shared.contracts.ports import HouseViewService
from shared.di.container import Container


def resolve() -> HouseViewService:
    container = Container()
    house_view.register(container)
    return container.resolve(HouseViewService)


def test_implements_port() -> None:
    assert isinstance(resolve(), HouseViewService)


async def test_methods_point_to_implementing_task() -> None:
    with pytest.raises(NotImplementedError, match="AH-14"):
        await resolve().chain("claim")
