import asyncio
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.news.config import load_config
from apps.services.news.feed import build_feed_client
from apps.services.news.ingest import ingest_news
from main import build_container
from shared.config.settings import Settings
from shared.contracts.ports import LLMGateway


async def main() -> None:
    config = load_config()
    container = build_container()
    try:
        llm = container.resolve(LLMGateway)
        budget_before = await llm.budget_left_rub()
        async with build_feed_client(config.fetch_timeout_seconds, config.user_agent) as http:
            result = await ingest_news(
                container.resolve(async_sessionmaker),
                llm,
                http,
                container.resolve(Settings).NEWS_RSS_URLS,
                config,
                datetime.now(UTC),
            )
        spent = budget_before - await llm.budget_left_rub()
        print(f"added: {result.added}")
        print(f"duplicates: {result.duplicates}")
        print(f"failed news: {', '.join(result.failed) or '-'}")
        print(f"failed feeds: {', '.join(result.failed_feeds) or '-'}")
        print(f"tokens in/out: {result.tokens_in}/{result.tokens_out}")
        print(f"spent: {spent:.4f} RUB")
        print(f"news in index: {result.total}")
    finally:
        await container.aclose()


if __name__ == "__main__":
    asyncio.run(main())
