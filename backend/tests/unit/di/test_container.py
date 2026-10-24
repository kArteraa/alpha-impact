import pytest

from shared.di.container import Container, MissingPortsError, UnknownPortError


class Port:
    pass


class Impl:
    pass


class Dependent:
    def __init__(self, dependency: object) -> None:
        self.dependency = dependency


def test_app_scope_returns_one_instance() -> None:
    container = Container()
    container.register(Port, lambda _: Impl())
    assert container.resolve(Port) is container.resolve(Port)


def test_request_scope_builds_instance_per_scope() -> None:
    container = Container()
    container.register(Port, lambda _: Impl(), scope="request")
    first = container.request_scope()
    second = container.request_scope()
    assert first.resolve(Port) is first.resolve(Port)
    assert first.resolve(Port) is not second.resolve(Port)


def test_request_scope_shares_app_instances() -> None:
    container = Container()
    container.register(Port, lambda _: Impl())
    assert container.request_scope().resolve(Port) is container.resolve(Port)


def test_factory_resolves_dependencies_through_container() -> None:
    container = Container()
    container.register(Port, lambda _: Impl())
    container.register(Dependent, lambda c: Dependent(c.resolve(Port)))
    assert container.resolve(Dependent).dependency is container.resolve(Port)


def test_unknown_port_raises() -> None:
    with pytest.raises(UnknownPortError, match="Port is not registered"):
        Container().resolve(Port)


def test_validate_lists_missing_ports() -> None:
    container = Container()
    container.register(Port, lambda _: Impl())
    with pytest.raises(MissingPortsError, match="Impl, Dependent") as info:
        container.validate([Port, Impl, Dependent])
    assert info.value.missing == ["Impl", "Dependent"]


async def test_aclose_runs_closers_in_reverse_order() -> None:
    container = Container()
    closed: list[str] = []

    async def close(name: str) -> None:
        closed.append(name)

    container.on_close(lambda: close("engine"))
    container.on_close(lambda: close("http"))
    await container.aclose()
    assert closed == ["http", "engine"]


async def test_aclose_runs_each_closer_once() -> None:
    container = Container()
    closed: list[str] = []

    async def close() -> None:
        closed.append("x")

    container.on_close(close)
    await container.aclose()
    await container.aclose()
    assert closed == ["x"]


async def test_request_scope_does_not_close_app_objects() -> None:
    container = Container()
    closed: list[str] = []

    async def close() -> None:
        closed.append("app")

    container.on_close(close)
    await container.request_scope().aclose()
    assert closed == []


async def test_app_object_built_from_request_scope_is_closed_by_root() -> None:
    container = Container()
    closed: list[str] = []

    async def close() -> None:
        closed.append("engine")

    def build(c: Container) -> Impl:
        c.on_close(close)
        return Impl()

    container.register(Port, build)
    container.request_scope().resolve(Port)
    await container.aclose()
    assert closed == ["engine"]
