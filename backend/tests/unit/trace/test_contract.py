import inspect
from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services import trace
from shared.contracts.ports import TraceStore
from shared.di.container import Container

PORT_METHODS = ("save", "get", "metrics", "feedback", "find_by_card")


def resolve() -> TraceStore:
    container = Container()
    container.register(async_sessionmaker, lambda _: MagicMock(spec=async_sessionmaker))
    trace.register(container)
    return container.resolve(TraceStore)


def test_implements_port() -> None:
    assert isinstance(resolve(), TraceStore)


def test_methods_cover_every_port_method() -> None:
    assert set(PORT_METHODS) == {
        name for name, _ in inspect.getmembers(TraceStore, inspect.iscoroutinefunction)
    }


@pytest.mark.parametrize("name", PORT_METHODS)
def test_registered_store_matches_port_signature(name: str) -> None:
    port_method = inspect.signature(getattr(TraceStore, name), eval_str=True)
    implementation = getattr(resolve(), name)
    assert inspect.iscoroutinefunction(implementation)
    assert inspect.signature(implementation, eval_str=True) == port_method.replace(
        parameters=list(port_method.parameters.values())[1:]
    )


async def test_find_by_card_points_to_implementing_task() -> None:
    with pytest.raises(NotImplementedError, match="AH-26"):
        await resolve().find_by_card("u1", "card-1")
