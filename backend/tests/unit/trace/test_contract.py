import inspect
from datetime import date
from typing import Any

import pytest

from apps.services import trace
from shared.contracts.ports import TraceStore
from shared.di.container import Container
from tests.integration.contracts.examples import TRACE

PORT_CALLS: dict[str, tuple[Any, ...]] = {
    "save": (TRACE,),
    "get": ("trace",),
    "metrics": (date(2026, 10, 22),),
    "feedback": ("u1", "card-1", True, None),
}


def resolve() -> TraceStore:
    container = Container()
    trace.register(container)
    return container.resolve(TraceStore)


def test_implements_port() -> None:
    assert isinstance(resolve(), TraceStore)


def test_calls_cover_every_port_method() -> None:
    assert set(PORT_CALLS) == {
        name for name, _ in inspect.getmembers(TraceStore, inspect.iscoroutinefunction)
    }


@pytest.mark.parametrize(("name", "arguments"), PORT_CALLS.items())
async def test_methods_point_to_implementing_task(name: str, arguments: tuple[Any, ...]) -> None:
    with pytest.raises(NotImplementedError, match="AH-23"):
        await getattr(resolve(), name)(*arguments)


@pytest.mark.parametrize("name", PORT_CALLS)
def test_registered_store_matches_port_signature(name: str) -> None:
    port_method = inspect.signature(getattr(TraceStore, name), eval_str=True)
    implementation = getattr(resolve(), name)
    assert inspect.iscoroutinefunction(implementation)
    assert inspect.signature(implementation, eval_str=True) == port_method.replace(
        parameters=list(port_method.parameters.values())[1:]
    )
