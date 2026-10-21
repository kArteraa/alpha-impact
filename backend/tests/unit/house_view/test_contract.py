from datetime import date

from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services import house_view
from shared.contracts.ports import HouseViewService
from shared.contracts.schemas import HouseViewClaim
from shared.di.container import Container


def test_implements_port() -> None:
    container = Container()
    container.register(async_sessionmaker, lambda _: async_sessionmaker())
    house_view.register(container)
    assert isinstance(container.resolve(HouseViewService), HouseViewService)


class WithoutVersion:
    async def claims(self, subject: str, as_of: date) -> list[HouseViewClaim]:
        return []

    async def chain(self, claim_id: str) -> list[HouseViewClaim]:
        return []


def test_port_requires_version() -> None:
    assert not isinstance(WithoutVersion(), HouseViewService)
