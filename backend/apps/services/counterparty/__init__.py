from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.counterparty.config import load_config
from apps.services.counterparty.service import CounterpartyAggregates
from shared.contracts.ports import CounterpartyService
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(
        CounterpartyService,
        lambda c: CounterpartyAggregates(c.resolve(async_sessionmaker), load_config()),
    )
