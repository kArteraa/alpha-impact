from collections.abc import Awaitable, Callable, Iterable
from typing import Any, Literal, cast

Scope = Literal["app", "request"]
Factory = Callable[["Container"], object]
Closer = Callable[[], Awaitable[None]]


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
        self._closers: list[Closer] = []
        self._is_root = True

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

    def on_close(self, closer: Closer) -> None:
        self._closers.append(closer)

    async def aclose(self) -> None:
        if not self._is_root:
            return
        closers = list(self._closers)
        self._closers.clear()
        for closer in reversed(closers):
            await closer()

    def request_scope(self) -> "Container":
        scope = Container()
        scope._registrations = self._registrations
        scope._app_instances = self._app_instances
        scope._closers = self._closers
        scope._is_root = False
        return scope
