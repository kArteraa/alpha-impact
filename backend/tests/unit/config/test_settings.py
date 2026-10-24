import pytest
from pydantic import ValidationError

from shared.config.settings import Settings


def test_reads_every_variable_from_environment(settings_env: dict[str, str]) -> None:
    settings = Settings(_env_file=None)
    assert settings.DB_URL == settings_env["DB_URL"]
    assert settings.MODEL_INTERPRET == settings_env["MODEL_INTERPRET"]
    assert settings.LLM_INTERACTIVE_TIMEOUT_SECONDS == 12
    assert settings.RELEVANCE_THRESHOLD == 0.3
    assert settings.CACHE_TTL_SECONDS == 3600
    assert settings.NEWS_RSS_URLS == ["https://a.example/rss", "https://b.example/rss"]
    assert settings.METRICS_PORT == 0


@pytest.mark.parametrize(
    "name",
    ["LLM_TIMEOUT_SECONDS", "LLM_INTERACTIVE_TIMEOUT_SECONDS", "EXTENSION_TOKEN_TTL_SECONDS"],
)
@pytest.mark.parametrize("value", ["0", "-1"])
def test_duration_must_be_positive(
    settings_env: dict[str, str], monkeypatch: pytest.MonkeyPatch, name: str, value: str
) -> None:
    monkeypatch.setenv(name, value)
    with pytest.raises(ValidationError, match=name):
        Settings(_env_file=None)


@pytest.mark.parametrize("value", ["-1", "65536"])
def test_metrics_port_must_be_a_tcp_port(
    settings_env: dict[str, str], monkeypatch: pytest.MonkeyPatch, value: str
) -> None:
    monkeypatch.setenv("METRICS_PORT", value)
    with pytest.raises(ValidationError, match="METRICS_PORT"):
        Settings(_env_file=None)


def test_daily_budget_defaults_to_500_rub(settings_env: dict[str, str]) -> None:
    assert Settings(_env_file=None).LLM_DAILY_BUDGET_RUB == 500


def test_missing_variable_fails_loudly(
    settings_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("DB_URL")
    with pytest.raises(ValidationError, match="DB_URL"):
        Settings(_env_file=None)
