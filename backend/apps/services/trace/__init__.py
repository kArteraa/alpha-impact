from apps.services.trace.service import TraceRepository
from shared.contracts.ports import TraceStore
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(TraceStore, lambda _: TraceRepository())
