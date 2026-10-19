from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    DB_URL: str
    LLM_API_BASE: str
    LLM_API_KEY: str
    LLM_DAILY_BUDGET_RUB: float = 500
    MODEL_ANNOTATE: str
    MODEL_EXTRACT: str
    MODEL_INTERPRET: str
    MODEL_CRITIC: str
    MODEL_FOLLOWUP: str
    RELEVANCE_THRESHOLD: float
    CACHE_TTL_SECONDS: int
    EXTENSION_TOKEN_TTL_SECONDS: int
    NEWS_RSS_URLS: list[str]
