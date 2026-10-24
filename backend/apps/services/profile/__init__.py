from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.profile.config import load_config
from apps.services.profile.service import Profiler
from shared.contracts.ports import ProfileService
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(
        ProfileService, lambda c: Profiler(c.resolve(async_sessionmaker), load_config())
    )
