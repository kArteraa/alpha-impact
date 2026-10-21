from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.house_view.service import HouseView
from shared.contracts.ports import HouseViewService
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(HouseViewService, lambda c: HouseView(c.resolve(async_sessionmaker)))
