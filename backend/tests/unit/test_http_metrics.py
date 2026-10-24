import socket

import httpx
import pytest
from fastapi import FastAPI
from prometheus_client import REGISTRY, generate_latest


@pytest.fixture
def app(settings_env: dict[str, str]) -> FastAPI:
    from main import create_app

    return create_app()


def sample(name: str, **labels: str) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0


def exposition() -> str:
    return generate_latest(REGISTRY).decode("utf-8")


def free_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port: int = probe.getsockname()[1]
        return port


async def get(app: FastAPI, path: str) -> httpx.Response:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def test_request_is_counted_by_route_status_and_duration(app: FastAPI) -> None:
    labels = {"method": "GET", "route": "/health"}
    requests = sample("http_requests_total", status="200", **labels)
    durations = sample("http_request_duration_seconds_count", **labels)
    await get(app, "/health")
    assert sample("http_requests_total", status="200", **labels) == requests + 1
    assert sample("http_request_duration_seconds_count", **labels) == durations + 1


async def test_route_label_is_the_path_template_not_the_identifier(app: FastAPI) -> None:
    labels = {"method": "GET", "route": "/profile/{client_id}", "status": "401"}
    before = sample("http_requests_total", **labels)
    response = await get(app, "/profile/client-7731")
    assert response.status_code == 401
    assert sample("http_requests_total", **labels) == before + 1
    assert "client-7731" not in exposition()


async def test_unknown_path_adds_no_series(app: FastAPI) -> None:
    response = await get(app, "/no-such-page")
    assert response.status_code == 404
    assert "no-such-page" not in exposition()


async def test_unhandled_error_is_counted_as_500(app: FastAPI) -> None:
    async def boom() -> None:
        raise RuntimeError("boom")

    app.add_api_route("/boom", boom)
    labels = {"method": "GET", "route": "/boom", "status": "500"}
    before = sample("http_requests_total", **labels)
    response = await get(app, "/boom")
    assert response.status_code == 500
    assert sample("http_requests_total", **labels) == before + 1


async def test_lifespan_serves_metrics_on_the_metrics_port_until_shutdown(
    settings_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    from main import create_app

    port = free_port()
    monkeypatch.setenv("METRICS_PORT", str(port))
    app = create_app()
    url = f"http://127.0.0.1:{port}/metrics"
    async with app.router.lifespan_context(app), httpx.AsyncClient() as client:
        response = await client.get(url)
    assert response.status_code == 200
    assert "http_requests_total" in response.text
    async with httpx.AsyncClient() as client:
        with pytest.raises(httpx.ConnectError):
            await client.get(url)
