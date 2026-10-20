from apps.services.profile.service import Profiler
from shared.contracts.ports import ProfileService
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(ProfileService, lambda _: Profiler())
