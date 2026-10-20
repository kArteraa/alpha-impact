from fastapi import APIRouter

from apps.services.gateway.router import router
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(APIRouter, lambda _: router)
