from fastapi import APIRouter

from apps.services import gateway
from shared.di.container import Container


def test_registers_router_with_bootstrap_routes() -> None:
    container = Container()
    gateway.register(container)
    router = container.resolve(APIRouter)
    paths = {getattr(route, "path", None) for route in router.routes}
    assert {
        "/health",
        "/auth/mock",
        "/clients",
        "/interpret",
        "/profile/{client_id}",
        "/profile/{client_id}/features/{name}",
        "/reports/{source_doc}",
    } <= paths
