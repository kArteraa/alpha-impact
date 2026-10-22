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


async def test_feedback_points_to_implementing_task() -> None:
    with pytest.raises(NotImplementedError, match="AH-23"):
        await resolve().feedback("u1", "card-1", useful=True, comment=None)


def test_port_declares_feedback() -> None:
    assert callable(getattr(TraceStore, "feedback", None))
