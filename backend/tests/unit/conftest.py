import pytest
from fastapi import FastAPI
from prometheus_client import REGISTRY

SETTINGS_ENV = {
    "DB_URL": "postgresql+asyncpg://alfa:alfa@localhost:5432/alfa",
    "LLM_API_BASE": "https://llm.example/v1",
    "LLM_API_KEY": "test-key",
    "LLM_TIMEOUT_SECONDS": "8",
    "LLM_INTERACTIVE_TIMEOUT_SECONDS": "12",
    "LLM_CALL_RESERVE_RUB": "1",
    "LLM_CACHE_TTL_SECONDS": "604800",
    "LLM_BUDGET_RESERVE_SHARE": "0.1",
    "MODEL_ANNOTATE": "google/gemma-4-26b-a4b-it",
    "MODEL_EXTRACT": "qwen/qwen3.6-35b-a3b",
    "MODEL_INTERPRET": "deepseek/deepseek-v4.1-flash",
    "MODEL_CRITIC": "z-ai/glm-5.3-flash",
    "MODEL_FOLLOWUP": "deepseek/deepseek-v4.1-flash",
    "RELEVANCE_THRESHOLD": "0.3",
    "CACHE_TTL_SECONDS": "3600",
    "EXTENSION_TOKEN_TTL_SECONDS": "3600",
    "NEWS_RSS_URLS": '["https://a.example/rss","https://b.example/rss"]',
    "METRICS_HOST": "127.0.0.1",
    "METRICS_PORT": "0",
}


@pytest.fixture
def settings_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    for name, value in SETTINGS_ENV.items():
        monkeypatch.setenv(name, value)
    return SETTINGS_ENV


@pytest.fixture
def app(settings_env: dict[str, str]) -> FastAPI:
    from main import create_app

    return create_app()


def sample(name: str, **labels: str) -> float:
    return REGISTRY.get_sample_value(name, labels) or 0.0
