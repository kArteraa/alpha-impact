import inspect

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


def test_port_declares_feedback_signature() -> None:
    signature = inspect.signature(TraceStore.feedback, eval_str=True)
    assert [(p.name, p.annotation) for p in signature.parameters.values()] == [
        ("self", inspect.Parameter.empty),
        ("user_id", str),
        ("card_id", str),
        ("useful", bool),
        ("comment", str | None),
    ]
    assert signature.return_annotation is None


@pytest.mark.parametrize("name", ["save", "get", "metrics", "feedback"])
def test_registered_store_matches_port_signature(name: str) -> None:
    port_method = inspect.signature(getattr(TraceStore, name), eval_str=True)
    implementation = getattr(resolve(), name)
    assert inspect.iscoroutinefunction(implementation)
    assert inspect.signature(implementation, eval_str=True) == port_method.replace(
        parameters=list(port_method.parameters.values())[1:]
    )
