from apps.services.house_view.service import HouseView
from shared.contracts.ports import HouseViewService
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(HouseViewService, lambda _: HouseView())
