from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


def create_engine(db_url: str) -> AsyncEngine:
    return create_async_engine(db_url)
