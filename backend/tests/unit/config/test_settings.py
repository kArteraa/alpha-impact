import pytest
from pydantic import ValidationError

from shared.config.settings import Settings


def test_reads_every_variable_from_environment(settings_env: dict[str, str]) -> None:
    settings = Settings(_env_file=None)
    assert settings.DB_URL == settings_env["DB_URL"]
    assert settings.MODEL_INTERPRET == "z-ai/glm-5.3-flash"
    assert settings.RELEVANCE_THRESHOLD == 0.3
    assert settings.CACHE_TTL_SECONDS == 3600
    assert settings.NEWS_RSS_URLS == ["https://a.example/rss", "https://b.example/rss"]


def test_daily_budget_defaults_to_500_rub(settings_env: dict[str, str]) -> None:
    assert Settings(_env_file=None).LLM_DAILY_BUDGET_RUB == 500


def test_missing_variable_fails_loudly(
    settings_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DB_URL")
    with pytest.raises(ValidationError, match="DB_URL"):
        Settings(_env_file=None)
