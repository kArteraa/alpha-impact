from datetime import date
from pathlib import Path

import pytest
from PIL import Image
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.house_view.ingest.config import Document, IngestConfig, load_config
from apps.services.house_view.ingest.pipeline import ingest_reports
from shared.contracts.errors import BudgetExceeded, DomainError
from shared.db.models import HouseViewClaimRow, ReportPageRow

RATE = Document(file="rate.pdf", title="Ставка", date=date(2026, 9, 11))
STEEL = Document(file="steel.pdf", title="Сталь", date=date(2021, 4, 15), expired=True)


PAGE_BREAK = "\n\n"
PAGE_TEXT = "Банк ожидает ключевую ставку 14% до конца года. " * 10


class FakeOcr:
    def __init__(self, text: str = PAGE_TEXT) -> None:
        self.calls = 0
        self.text = text

    def read(self, image: bytes) -> str:
        self.calls += 1
        return f"страница {self.calls}: {self.text}"


class FakeLlm:
    def __init__(self, errors: list[DomainError] | None = None) -> None:
        self.calls: list[str] = []
        self.errors = errors or []

    async def complete(
        self, task: str, system: str, user: str, schema: type | None = None
    ) -> tuple[object, int, int, float]:
        assert schema is not None and issubclass(schema, BaseModel)
        self.calls.append(task)
        if self.errors:
            raise self.errors.pop(0)
        claim = {
            "claim": f"Банк ждёт ставку 14% ({user.split(PAGE_BREAK, 1)[1][:12]})",
            "type": "forecast",
            "subject": "key_rate",
            "value": "14%",
            "valid_until": None,
        }
        return schema.model_validate({"claims": [claim]}), 100, 20, 0.0

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError

    async def budget_left_rub(self) -> float:
        return 100.0


def write_pdf(path: Path, pages: int, shade: int = 90) -> None:
    images = [Image.new("RGB", (40, 60), (index * 40, shade, 90)) for index in range(pages)]
    images[0].save(path, save_all=True, append_images=images[1:])


@pytest.fixture
def config(tmp_path: Path) -> IngestConfig:
    write_pdf(tmp_path / RATE.file, 2)
    write_pdf(tmp_path / STEEL.file, 1)
    return load_config().model_copy(update={"documents": [RATE, STEEL]})


async def count(sessions: async_sessionmaker[AsyncSession], model: type) -> int:
    async with sessions() as session:
        return int(await session.scalar(select(func.count()).select_from(model)) or 0)


async def test_reports_become_pages_and_draft_claims(
    sessions: async_sessionmaker[AsyncSession], config: IngestConfig, tmp_path: Path
) -> None:
    ocr, llm = FakeOcr(), FakeLlm()

    result = await ingest_reports(sessions, llm, ocr, tmp_path, config)

    assert (result.pages, result.claims) == (3, 3)
    assert llm.calls == ["extract"] * 3
    assert await count(sessions, ReportPageRow) == 3
    async with sessions() as session:
        rows = (await session.scalars(select(HouseViewClaimRow))).all()
    statuses = {(row.source_doc, row.status) for row in rows}
    assert statuses == {(RATE.file, "draft"), (STEEL.file, "expired")}
    assert {row.date for row in rows if row.source_doc == RATE.file} == {RATE.date}
    assert {row.page for row in rows if row.source_doc == RATE.file} == {1, 2}


async def test_rerun_skips_ocr_and_adds_no_duplicates(
    sessions: async_sessionmaker[AsyncSession], config: IngestConfig, tmp_path: Path
) -> None:
    ocr, llm = FakeOcr(), FakeLlm()
    await ingest_reports(sessions, llm, ocr, tmp_path, config)

    await ingest_reports(sessions, llm, ocr, tmp_path, config)

    assert ocr.calls == 3
    assert llm.calls == ["extract"] * 3
    assert await count(sessions, ReportPageRow) == 3
    assert await count(sessions, HouseViewClaimRow) == 3


async def test_rerun_keeps_reviewed_status(
    sessions: async_sessionmaker[AsyncSession], config: IngestConfig, tmp_path: Path
) -> None:
    ocr, llm = FakeOcr(), FakeLlm()
    await ingest_reports(sessions, llm, ocr, tmp_path, config)
    async with sessions() as session, session.begin():
        row = await session.scalar(select(HouseViewClaimRow).limit(1))
        assert row is not None
        row.status = "approved"
        approved = row.id

    await ingest_reports(sessions, llm, ocr, tmp_path, config)

    async with sessions() as session:
        reviewed = await session.get(HouseViewClaimRow, approved)
    assert reviewed is not None
    assert reviewed.status == "approved"


async def test_missing_report_file_fails(
    sessions: async_sessionmaker[AsyncSession], config: IngestConfig, tmp_path: Path
) -> None:
    missing = config.model_copy(
        update={"documents": [Document(file="absent.pdf", title="—", date=date(2026, 1, 1))]}
    )

    with pytest.raises(FileNotFoundError):
        await ingest_reports(sessions, FakeLlm(), FakeOcr(), tmp_path, missing)


async def test_page_without_text_is_not_sent_to_model(
    sessions: async_sessionmaker[AsyncSession], config: IngestConfig, tmp_path: Path
) -> None:
    llm = FakeLlm()

    result = await ingest_reports(sessions, llm, FakeOcr(text="Итоги"), tmp_path, config)

    assert (result.pages, result.claims) == (3, 0)
    assert llm.calls == []
    async with sessions() as session:
        pending = await session.scalar(
            select(func.count())
            .select_from(ReportPageRow)
            .where(ReportPageRow.extracted.is_(False))
        )
    assert pending == 0


async def test_page_the_model_failed_on_is_reported_and_retried(
    sessions: async_sessionmaker[AsyncSession], config: IngestConfig, tmp_path: Path
) -> None:
    llm = FakeLlm(errors=[DomainError("answer does not match")])

    result = await ingest_reports(sessions, llm, FakeOcr(), tmp_path, config)

    assert (result.claims, result.failed) == (2, (f"{RATE.file}:1",))
    retry = FakeLlm()
    result = await ingest_reports(sessions, retry, FakeOcr(), tmp_path, config)
    assert (result.claims, result.failed, retry.calls) == (3, (), ["extract"])


async def test_spent_budget_stops_the_run(
    sessions: async_sessionmaker[AsyncSession], config: IngestConfig, tmp_path: Path
) -> None:
    llm = FakeLlm(errors=[BudgetExceeded("spent")])

    with pytest.raises(BudgetExceeded):
        await ingest_reports(sessions, llm, FakeOcr(), tmp_path, config)


async def test_replaced_report_drops_claims_of_its_old_pages(
    sessions: async_sessionmaker[AsyncSession], config: IngestConfig, tmp_path: Path
) -> None:
    ocr = FakeOcr()
    await ingest_reports(sessions, FakeLlm(), ocr, tmp_path, config)
    async with sessions() as session, session.begin():
        row = await session.scalar(
            select(HouseViewClaimRow).where(HouseViewClaimRow.source_doc == RATE.file)
        )
        assert row is not None
        stale = row.id
    write_pdf(tmp_path / RATE.file, 1, shade=150)
    llm = FakeLlm()

    result = await ingest_reports(sessions, llm, ocr, tmp_path, config)

    assert (ocr.calls, llm.calls) == (4, ["extract"])
    assert (result.pages, result.claims) == (2, 2)
    async with sessions() as session:
        rows = (await session.scalars(select(HouseViewClaimRow))).all()
    assert stale not in {row.id for row in rows}
    assert {(row.source_doc, row.page) for row in rows} == {(RATE.file, 1), (STEEL.file, 1)}


async def test_page_longer_than_limit_is_reported(
    sessions: async_sessionmaker[AsyncSession], config: IngestConfig, tmp_path: Path
) -> None:
    short = config.model_copy(update={"max_page_chars": 300})

    result = await ingest_reports(sessions, FakeLlm(), FakeOcr(), tmp_path, short)

    assert result.truncated == (f"{RATE.file}:1", f"{RATE.file}:2", f"{STEEL.file}:1")
