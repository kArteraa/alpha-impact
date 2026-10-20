import asyncio
import hashlib
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.house_view.ingest.config import Document, IngestConfig
from apps.services.house_view.ingest.extract import extraction_schema, to_claims
from apps.services.house_view.ingest.ocr import Ocr
from apps.services.house_view.ingest.pages import page_images
from apps.services.house_view.ingest.repository import (
    add_claims,
    cached_text,
    claim_count,
    document_pages,
    save_page,
)
from shared.contracts.ports import LLMGateway


@dataclass(frozen=True)
class IngestResult:
    pages: int
    claims: int


async def recognize(
    sessions: async_sessionmaker[AsyncSession], ocr: Ocr, path: Path, document: Document
) -> int:
    images = page_images(path)
    for number, image in enumerate(images, start=1):
        digest = hashlib.sha256(image).hexdigest()
        async with sessions() as session, session.begin():
            if await cached_text(session, document.file, number, digest) is None:
                text = await asyncio.to_thread(ocr.read, image)
                await save_page(session, document.file, number, digest, text)
    return len(images)


def page_prompt(document: Document, page: int, text: str, config: IngestConfig) -> str:
    return (
        f"Документ: {document.title}\nДата выпуска: {document.date.isoformat()}\n"
        f"Страница: {page}\n\n{text[: config.max_page_chars]}"
    )


async def extract(
    sessions: async_sessionmaker[AsyncSession],
    llm: LLMGateway,
    document: Document,
    config: IngestConfig,
) -> None:
    schema = extraction_schema(config.subjects)
    async with sessions() as session:
        pages = await document_pages(session, document.file)
    for page in pages:
        answer, _, _ = await llm.complete(
            config.llm_task,
            config.system_prompt,
            page_prompt(document, page.page, page.text, config),
            schema,
        )
        assert isinstance(answer, schema)
        async with sessions() as session, session.begin():
            await add_claims(session, to_claims(answer, document, page.page))


async def ingest_reports(
    sessions: async_sessionmaker[AsyncSession],
    llm: LLMGateway,
    ocr: Ocr,
    raw_dir: Path,
    config: IngestConfig,
) -> IngestResult:
    paths = {document.file: raw_dir / document.file for document in config.documents}
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Reports not found in {raw_dir}: {', '.join(missing)}")
    pages = 0
    for document in config.documents:
        pages += await recognize(sessions, ocr, paths[document.file], document)
    for document in config.documents:
        await extract(sessions, llm, document, config)
    async with sessions() as session:
        return IngestResult(pages=pages, claims=await claim_count(session))
