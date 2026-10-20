import pytest

from apps.services import trace
from shared.contracts.ports import TraceStore
from shared.di.container import Container


def resolve() -> TraceStore:
    container = Container()
    trace.register(container)
    return container.resolve(TraceStore)


def test_implements_port() -> None:
    assert isinstance(resolve(), TraceStore)


async def test_methods_point_to_implementing_task() -> None:
    with pytest.raises(NotImplementedError, match="AH-23"):
        await resolve().get("trace")
