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
from shared.contracts import ports
from shared.contracts.ports import Interpreter
from shared.di.container import Container, MissingPortsError

SERVICES_DIR = Path(apps.services.__file__).parent

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
    before = set(sys.modules)
    yield tmp_path
    for name in set(sys.modules) - before:
        if name.startswith(f"{apps.services.__name__}."):
            del sys.modules[name]


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


def test_discover_services_finds_every_service_package() -> None:
    from main import discover_services

    packages = sorted(p.name for p in SERVICES_DIR.iterdir() if (p / "__init__.py").is_file())
    assert [module.__name__.rsplit(".", 1)[1] for module in discover_services()] == packages


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


def test_missing_registration_fails_start_with_port_name() -> None:
    from main import all_ports

    container = Container()
    for port in all_ports():
        if port is not ports.TraceStore:
            container.register(port, lambda _: object())
    with pytest.raises(MissingPortsError, match="TraceStore"):
        container.validate(all_ports())
