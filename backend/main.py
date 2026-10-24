import importlib
import pkgutil
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from http import HTTPStatus
from time import perf_counter
from types import ModuleType
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from prometheus_client import Counter, Histogram, start_http_server
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker
from starlette.types import ASGIApp, Message, Receive, Scope, Send

import apps.services
from shared.config.settings import Settings
from shared.contracts import ports
from shared.db.engine import create_engine
from shared.db.session import make_session_factory
from shared.di.container import Container

LATENCY_BUCKETS_SECONDS = (0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, 20, 40)
HTTP_REQUESTS = Counter(
    "http_requests", "HTTP requests by route and status", ["method", "route", "status"]
)
HTTP_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration by route",
    ["method", "route"],
    buckets=LATENCY_BUCKETS_SECONDS,
)


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


def build_engine(container: Container) -> AsyncEngine:
    engine = create_engine(container.resolve(Settings).DB_URL)
    container.on_close(engine.dispose)
    return engine


def build_container() -> Container:
    container = Container()
    container.register(Settings, lambda _: Settings())
    container.register(AsyncEngine, build_engine)
    container.register(async_sessionmaker, lambda c: make_session_factory(c.resolve(AsyncEngine)))
    for service in discover_services():
        service.register(container)
    container.validate(all_ports())
    return container


class HttpMetrics:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        start = perf_counter()
        statuses: list[int] = []

        async def capture(message: Message) -> None:
            if message["type"] == "http.response.start":
                statuses.append(message["status"])
            await send(message)

        try:
            await self._app(scope, receive, capture)
        finally:
            route = scope.get("route")
            if isinstance(route, APIRoute):
                status = statuses[0] if statuses else HTTPStatus.INTERNAL_SERVER_ERROR.value
                HTTP_REQUESTS.labels(scope["method"], route.path_format, str(status)).inc()
                HTTP_DURATION.labels(scope["method"], route.path_format).observe(
                    perf_counter() - start
                )


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    server, _ = start_http_server(app.state.container.resolve(Settings).METRICS_PORT)
    yield
    server.shutdown()
    server.server_close()
    await app.state.container.aclose()


def create_app() -> FastAPI:
    container = build_container()
    app = FastAPI(title="Alpha Impact", lifespan=lifespan)
    app.state.container = container
    app.include_router(container.resolve(APIRouter))
    app.add_middleware(HttpMetrics)
    return app


app = create_app()
