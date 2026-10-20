from typing import Any

from apps.services import (
    counterparty,
    gateway,
    house_view,
    interpreter,
    llm,
    news,
    products,
    profile,
    trace,
    whatif,
)
from shared.contracts import ports
from shared.di.container import Container

SERVICES = (
    gateway,
    profile,
    counterparty,
    news,
    house_view,
    interpreter,
    whatif,
    products,
    llm,
    trace,
)


def all_ports() -> list[type[Any]]:
    return [
        obj
        for obj in vars(ports).values()
        if isinstance(obj, type)
        and obj.__module__ == ports.__name__
        and getattr(obj, "_is_protocol", False)
    ]


def wire(container: Container) -> Container:
    for service in SERVICES:
        service.register(container)
    container.validate(all_ports())
    return container
