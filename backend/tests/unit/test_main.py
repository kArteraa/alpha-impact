import importlib
import sys
from collections.abc import Iterator
from pathlib import Path

import httpx
import pytest
from fastapi import APIRouter, FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

import apps.services
from shared.config.settings import Settings
from shared.contracts.ports import Interpreter
from shared.di.container import Container

EXPECTED_PORTS = {
    "ProfileService",
    "CounterpartyService",
    "NewsService",
    "PageContextService",
    "HouseViewService",
    "WhatIfService",
    "ProductRulesService",
    "LLMGateway",
    "TraceStore",
    "Critic",
    "Interpreter",
}

PROBE_SERVICE = """
from shared.config.settings import Settings
from shared.di.container import Container


class Probe:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings


def register(container: Container) -> None:
    container.register(Probe, lambda c: Probe(c.resolve(Settings)))
"""


@pytest.fixture
def app(settings_env: dict[str, str]) -> FastAPI:
    from main import create_app

    return create_app()


@pytest.fixture
def extra_services_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setattr(apps.services, "__path__", [*apps.services.__path__, str(tmp_path)])
    yield tmp_path
    for name, module in list(sys.modules.items()):
        if Path(getattr(module, "__file__", None) or "").is_relative_to(tmp_path):
            del sys.modules[name]
            vars(apps.services).pop(name.rsplit(".", 1)[1], None)


def add_service(directory: Path, name: str, source: str) -> None:
    package = directory / name
    package.mkdir()
    (package / "__init__.py").write_text(source, encoding="utf-8")


async def test_health_answers(app: FastAPI) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_container_is_wired_into_app_state(app: FastAPI) -> None:
    container: Container = app.state.container
    assert isinstance(container.resolve(Interpreter), Interpreter)
    assert isinstance(container.resolve(APIRouter), APIRouter)


def test_all_ports_covers_every_protocol_in_ports_module() -> None:
    from main import all_ports

    assert {port.__name__ for port in all_ports()} == EXPECTED_PORTS


def test_build_container_registers_an_implementation_for_every_port(
    settings_env: dict[str, str],
) -> None:
    from main import all_ports, build_container

    container = build_container()
    for port in all_ports():
        assert isinstance(container.resolve(port), port)


def test_service_factories_receive_settings_and_session_factory(
    settings_env: dict[str, str],
) -> None:
    from main import build_container

    container = build_container()
    assert container.resolve(Settings).DB_URL == settings_env["DB_URL"]
    assert isinstance(container.resolve(async_sessionmaker), async_sessionmaker)


def test_new_service_is_registered_without_editing_shared_files(
    settings_env: dict[str, str], extra_services_dir: Path
) -> None:
    from main import build_container, discover_services

    add_service(extra_services_dir, "probe", PROBE_SERVICE)
    probe = importlib.import_module("apps.services.probe")

    assert probe in discover_services()
    assert build_container().resolve(probe.Probe).settings.DB_URL == settings_env["DB_URL"]


def test_service_without_register_fails_the_build(
    settings_env: dict[str, str], extra_services_dir: Path
) -> None:
    from main import build_container

    add_service(extra_services_dir, "broken", "")

    with pytest.raises(AttributeError, match="apps.services.broken"):
        build_container()
