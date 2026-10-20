import httpx
import pytest
from fastapi import APIRouter, FastAPI

from shared.contracts.ports import Interpreter
from shared.di.container import Container


@pytest.fixture
def app(settings_env: dict[str, str]) -> FastAPI:
    from main import create_app

    return create_app()


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
