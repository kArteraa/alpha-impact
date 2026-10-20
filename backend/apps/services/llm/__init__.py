from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.llm.catalog import MODELS_PATH, build_catalog, load_prices
from apps.services.llm.client import ModelClient, build_http_client
from apps.services.llm.embedder import build_embedder
from apps.services.llm.service import ModelGateway
from apps.services.llm.store import SqlUsageStore
from shared.config.settings import Settings
from shared.contracts.ports import LLMGateway
from shared.di.container import Container

__all__ = ["register"]


def utc_today() -> date:
    return datetime.now(UTC).date()


def build_gateway(container: Container) -> ModelGateway:
    settings = container.resolve(Settings)
    http = build_http_client(settings)
    container.on_close(http.aclose)
    return ModelGateway(
        catalog=build_catalog(settings, load_prices(MODELS_PATH)),
        client=ModelClient(http),
        embedder=build_embedder(),
        store=SqlUsageStore(container.resolve(async_sessionmaker), settings.LLM_CACHE_TTL_SECONDS),
        daily_budget_rub=settings.LLM_DAILY_BUDGET_RUB,
        reserve_share=settings.LLM_BUDGET_RESERVE_SHARE,
        call_reserve_rub=settings.LLM_CALL_RESERVE_RUB,
        today=utc_today,
    )


def register(container: Container) -> None:
    container.register(LLMGateway, build_gateway)
