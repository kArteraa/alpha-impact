from fastapi import APIRouter
from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.gateway.cache import SqlInterpretCache
from apps.services.gateway.calls import SqlCallJournal
from apps.services.gateway.reports import ReportFiles
from apps.services.gateway.router import router
from apps.services.gateway.service import InterpretGateway
from shared.config.paths import RAW_DIR
from shared.config.settings import Settings
from shared.contracts.ports import HouseViewService, Interpreter, ProfileService
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(APIRouter, lambda _: router)
    container.register(ReportFiles, lambda _: ReportFiles(RAW_DIR))
    container.register(
        InterpretGateway,
        lambda c: InterpretGateway(
            interpreter=c.resolve(Interpreter),
            house_view=c.resolve(HouseViewService),
            profiles=c.resolve(ProfileService),
            cache=SqlInterpretCache(
                c.resolve(async_sessionmaker), c.resolve(Settings).CACHE_TTL_SECONDS
            ),
            journal=SqlCallJournal(c.resolve(async_sessionmaker)),
        ),
    )
