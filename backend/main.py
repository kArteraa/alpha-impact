import importlib
import pkgutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from types import ModuleType
from typing import Any

from fastapi import APIRouter, FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

import apps.services
from shared.config.settings import Settings
from shared.contracts import ports
from shared.db.engine import create_engine
from shared.db.session import make_session_factory
from shared.di.container import Container


def discover_services() -> list[ModuleType]:
    packages = sorted(
        module.name for module in pkgutil.iter_modules(apps.services.__path__) if module.ispkg
    )
    return [importlib.import_module(f"{apps.services.__name__}.{name}") for name in packages]


def all_ports() -> list[type[Any]]:
    return [
        obj
        for obj in vars(ports).values()
        if isinstance(obj, type)
        and obj.__module__ == ports.__name__
        and getattr(obj, "_is_protocol", False)
    ]


def build_container() -> Container:
    container = Container()
    container.register(Settings, lambda _: Settings())
    container.register(AsyncEngine, lambda c: create_engine(c.resolve(Settings).DB_URL))
    container.register(async_sessionmaker, lambda c: make_session_factory(c.resolve(AsyncEngine)))
    for service in discover_services():
        service.register(container)
    container.validate(all_ports())
    return container


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.container.resolve(AsyncEngine).dispose()


def create_app() -> FastAPI:
    container = build_container()
    app = FastAPI(title="Alpha Impact", lifespan=lifespan)
    app.state.container = container
    app.include_router(container.resolve(APIRouter))
    return app


app = create_app()
