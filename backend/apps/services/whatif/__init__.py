from apps.services.whatif.service import Calculator
from shared.contracts.ports import WhatIfService
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(WhatIfService, lambda _: Calculator())
