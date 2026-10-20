import asyncio
import hashlib
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.house_view.ingest.config import Document, IngestConfig
from apps.services.house_view.ingest.extract import Extraction, extraction_schema, to_claims
from apps.services.house_view.ingest.ocr import Ocr
from apps.services.house_view.ingest.pages import page_images
from apps.services.house_view.ingest.repository import (
    add_claims,
    cached_text,
    claim_count,
    drop_page_claims,
    drop_pages_after,
    mark_extracted,
    pending_pages,
    save_page,
)
from shared.contracts.errors import BudgetExceeded, DomainError
from shared.contracts.ports import LLMGateway


@dataclass(frozen=True)
class IngestResult:
    pages: int
    claims: int
    failed: tuple[str, ...]
    truncated: tuple[str, ...]


@dataclass(frozen=True)
class ExtractReport:
    failed: tuple[str, ...]
    truncated: tuple[str, ...]


def place(document: Document, page: int) -> str:
    return f"{document.file}:{page}"


async def recognize(
    sessions: async_sessionmaker[AsyncSession], ocr: Ocr, path: Path, document: Document
) -> int:
    images = page_images(path)
    async with sessions() as session, session.begin():
        await drop_pages_after(session, document.file, len(images))
    for number, image in enumerate(images, start=1):
        digest = hashlib.sha256(image).hexdigest()
        async with sessions() as session, session.begin():
            if await cached_text(session, document.file, number, digest) is None:
                text = await asyncio.to_thread(ocr.read, image)
                await drop_page_claims(session, document.file, number)
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
) -> ExtractReport:
    schema = extraction_schema(config.subjects, config.max_claims_per_page)
    failed: list[str] = []
    truncated: list[str] = []
    async with sessions() as session:
        pages = await pending_pages(session, document.file)
    for page in pages:
        if len(page.text.strip()) < config.min_page_chars:
            async with sessions() as session, session.begin():
                await mark_extracted(session, document.file, page.page)
            continue
        if len(page.text) > config.max_page_chars:
            truncated.append(place(document, page.page))
        try:
            answer, _, _ = await llm.complete(
                config.llm_task,
                config.prompt,
                page_prompt(document, page.page, page.text, config),
                schema,
            )
        except BudgetExceeded:
            raise
        except DomainError:
            failed.append(place(document, page.page))
            continue
        if not isinstance(answer, Extraction):
            raise TypeError(f"LLM gateway returned {type(answer).__name__}, not {schema.__name__}")
        async with sessions() as session, session.begin():
            await add_claims(session, to_claims(answer.claims, document, page.page))
            await mark_extracted(session, document.file, page.page)
    return ExtractReport(failed=tuple(failed), truncated=tuple(truncated))


async def ingest_reports(
    sessions: async_sessionmaker[AsyncSession],
    llm: LLMGateway,
    ocr: Ocr,
    raw_dir: Path,
    config: IngestConfig,
) -> IngestResult:
    missing = [doc.file for doc in config.documents if not (raw_dir / doc.file).is_file()]
    if missing:
        raise FileNotFoundError(f"Reports not found in {raw_dir}: {', '.join(missing)}")
    pages = 0
    for document in config.documents:
        pages += await recognize(sessions, ocr, raw_dir / document.file, document)
    reports = [await extract(sessions, llm, document, config) for document in config.documents]
    async with sessions() as session:
        return IngestResult(
            pages=pages,
            claims=await claim_count(session),
            failed=tuple(item for report in reports for item in report.failed),
            truncated=tuple(item for report in reports for item in report.truncated),
        )
