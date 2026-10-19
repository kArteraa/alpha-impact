from collections.abc import Callable, Iterable
from typing import Any, Literal, cast

Scope = Literal["app", "request"]
Factory = Callable[["Container"], object]


class MissingPortsError(RuntimeError):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__("Ports without registration: " + ", ".join(missing))


class UnknownPortError(LookupError):
    def __init__(self, port: type[Any]) -> None:
        super().__init__(f"Port {port.__name__} is not registered")


class Container:
    def __init__(self) -> None:
        self._registrations: dict[type[Any], tuple[Factory, Scope]] = {}
        self._app_instances: dict[type[Any], object] = {}
        self._request_instances: dict[type[Any], object] = {}

    def register(self, port: type[Any], factory: Factory, scope: Scope = "app") -> None:
        self._registrations[port] = (factory, scope)

    def resolve[T](self, port: type[T]) -> T:
        registration = self._registrations.get(port)
        if registration is None:
            raise UnknownPortError(port)
        factory, scope = registration
        cache = self._app_instances if scope == "app" else self._request_instances
        if port not in cache:
            cache[port] = factory(self)
        return cast(T, cache[port])

    def validate(self, required_ports: Iterable[type[Any]]) -> None:
        missing = [port.__name__ for port in required_ports if port not in self._registrations]
        if missing:
            raise MissingPortsError(missing)

    def request_scope(self) -> "Container":
        scope = Container()
        scope._registrations = self._registrations
        scope._app_instances = self._app_instances
        return scope
