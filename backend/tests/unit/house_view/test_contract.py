from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services import house_view
from shared.contracts.ports import HouseViewService
from shared.di.container import Container


def test_implements_port() -> None:
    container = Container()
    container.register(async_sessionmaker, lambda _: async_sessionmaker())
    house_view.register(container)
    assert isinstance(container.resolve(HouseViewService), HouseViewService)
