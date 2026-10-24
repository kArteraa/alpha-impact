from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services import counterparty
from shared.contracts.ports import CounterpartyService
from shared.di.container import Container


def test_implements_port() -> None:
    container = Container()
    container.register(async_sessionmaker, lambda _: async_sessionmaker())
    counterparty.register(container)
    assert isinstance(container.resolve(CounterpartyService), CounterpartyService)
