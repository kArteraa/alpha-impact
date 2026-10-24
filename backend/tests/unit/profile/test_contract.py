from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services import profile
from shared.contracts.ports import ProfileService
from shared.di.container import Container


def test_implements_port() -> None:
    container = Container()
    container.register(async_sessionmaker, lambda _: async_sessionmaker())
    profile.register(container)
    assert isinstance(container.resolve(ProfileService), ProfileService)
