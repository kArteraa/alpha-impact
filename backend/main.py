from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from shared.config.settings import Settings
from shared.db.engine import create_engine
from shared.db.session import make_session_factory
from shared.di.container import Container
from shared.di.wiring import wire


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    yield
    await app.state.container.resolve(AsyncEngine).dispose()


def create_app() -> FastAPI:
    container = Container()
    container.register(Settings, lambda _: Settings())
    container.register(AsyncEngine, lambda c: create_engine(c.resolve(Settings).DB_URL))
    container.register(async_sessionmaker, lambda c: make_session_factory(c.resolve(AsyncEngine)))
    wire(container)
    app = FastAPI(title="alfa-insight", lifespan=lifespan)
    app.state.container = container
    app.include_router(container.resolve(APIRouter))
    return app


app = create_app()
