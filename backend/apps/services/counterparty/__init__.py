from apps.services.counterparty.service import CounterpartyAggregates
from shared.contracts.ports import CounterpartyService
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(CounterpartyService, lambda _: CounterpartyAggregates())
