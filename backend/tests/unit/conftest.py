import pytest

SETTINGS_ENV = {
    "DB_URL": "postgresql+asyncpg://alfa:alfa@localhost:5432/alfa",
    "LLM_API_BASE": "https://llm.example/v1",
    "LLM_API_KEY": "test-key",
    "LLM_TIMEOUT_SECONDS": "8",
    "LLM_BUDGET_RESERVE_SHARE": "0.1",
    "MODEL_ANNOTATE": "gemma-4-26b-a4b",
    "MODEL_EXTRACT": "qwen3.6-35b-a3b",
    "MODEL_INTERPRET": "glm-5.3-flash",
    "MODEL_CRITIC": "glm-5.3-flash",
    "MODEL_FOLLOWUP": "qwen3.6-35b-a3b",
    "MODEL_EMBED": "tbd-embedding-model",
    "RELEVANCE_THRESHOLD": "0.3",
    "CACHE_TTL_SECONDS": "3600",
    "EXTENSION_TOKEN_TTL_SECONDS": "3600",
    "NEWS_RSS_URLS": '["https://a.example/rss","https://b.example/rss"]',
}


@pytest.fixture
def settings_env(monkeypatch: pytest.MonkeyPatch) -> dict[str, str]:
    for name, value in SETTINGS_ENV.items():
        monkeypatch.setenv(name, value)
    return SETTINGS_ENV
