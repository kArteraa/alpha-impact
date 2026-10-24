import os
from collections.abc import AsyncIterator, Iterator
from concurrent.futures import ThreadPoolExecutor

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from shared.db.session import make_session_factory

MIGRATED_TABLES = text(
    "SELECT tablename FROM pg_tables "
    "WHERE schemaname = current_schema() AND tablename <> 'alembic_version'"
)


def run_alembic(action: str, revision: str) -> None:
    config = Config("alembic.ini")
    with ThreadPoolExecutor(max_workers=1) as executor:
        executor.submit(getattr(command, action), config, revision).result()


@pytest.fixture(scope="session")
def migrated_db() -> Iterator[str]:
    url = os.environ["TEST_DB_URL"]
    previous = os.environ.get("DB_URL")
    os.environ["DB_URL"] = url
    run_alembic("upgrade", "head")
    yield url
    run_alembic("downgrade", "base")
    if previous is None:
        del os.environ["DB_URL"]
    else:
        os.environ["DB_URL"] = previous


@pytest.fixture
async def engine(migrated_db: str) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(migrated_db, poolclass=NullPool)
    async with engine.begin() as connection:
        tables = (await connection.scalars(MIGRATED_TABLES)).all()
        await connection.execute(text(f"TRUNCATE {', '.join(tables)} CASCADE"))
    yield engine
    await engine.dispose()


@pytest.fixture
def sessions(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return make_session_factory(engine)
