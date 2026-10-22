import asyncio

from sqlalchemy.ext.asyncio import async_sessionmaker

from apps.services.news.config import load_config
from apps.services.news.reannotate import reannotate_news
from main import build_container
from shared.contracts.ports import LLMGateway


async def main() -> None:
    container = build_container()
    try:
        llm = container.resolve(LLMGateway)
        budget_before = await llm.budget_left_rub()
        result = await reannotate_news(container.resolve(async_sessionmaker), llm, load_config())
        spent = budget_before - await llm.budget_left_rub()
        print(f"updated: {result.updated}")
        print(f"failed news: {', '.join(result.failed) or '-'}")
        print(f"tokens in/out: {result.tokens_in}/{result.tokens_out}")
        print(f"spent: {spent:.4f} RUB")
    finally:
        await container.aclose()


if __name__ == "__main__":
    asyncio.run(main())
