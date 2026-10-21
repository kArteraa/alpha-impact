from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.news.annotation import annotate, annotation_schema, entities, news_factors
from apps.services.news.config import NewsConfig
from apps.services.news.repository import stored_news, update_annotation
from shared.contracts.errors import BudgetExceeded, DomainError
from shared.contracts.ports import LLMGateway


@dataclass(frozen=True)
class ReannotateResult:
    updated: int
    failed: tuple[str, ...]
    tokens_in: int
    tokens_out: int


async def reannotate_news(
    sessions: async_sessionmaker[AsyncSession], llm: LLMGateway, config: NewsConfig
) -> ReannotateResult:
    async with sessions() as session:
        stored = await stored_news(session)
    schema = annotation_schema(config)
    updated = tokens_in = tokens_out = 0
    failed: list[str] = []
    for news_id, url, title, text in stored:
        try:
            annotation, used_in, used_out = await annotate(llm, config, schema, title, text)
        except BudgetExceeded:
            raise
        except DomainError:
            failed.append(url)
            continue
        async with sessions() as session, session.begin():
            await update_annotation(
                session, news_id, entities(annotation), news_factors(annotation)
            )
        updated += 1
        tokens_in += used_in
        tokens_out += used_out
    return ReannotateResult(updated, tuple(failed), tokens_in, tokens_out)
