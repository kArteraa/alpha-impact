from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.trace.service import TraceRepository
from shared.contracts.ports import TraceStore
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(TraceStore, lambda c: TraceRepository(c.resolve(async_sessionmaker)))
