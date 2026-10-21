from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    DB_URL: str
    LLM_API_BASE: str
    LLM_API_KEY: str
    LLM_DAILY_BUDGET_RUB: float = 500
    LLM_BUDGET_RESERVE_SHARE: float
    LLM_TIMEOUT_SECONDS: float
    LLM_CALL_RESERVE_RUB: float
    LLM_CACHE_TTL_SECONDS: int
    MODEL_ANNOTATE: str
    MODEL_EXTRACT: str
    MODEL_INTERPRET: str
    MODEL_CRITIC: str
    MODEL_FOLLOWUP: str
    RELEVANCE_THRESHOLD: float
    CACHE_TTL_SECONDS: int
    EXTENSION_TOKEN_TTL_SECONDS: int
    NEWS_RSS_URLS: list[str]
