from pathlib import Path

import pytest

from apps.services.gateway.reports import ReportFiles
from shared.contracts.errors import NotFound


@pytest.fixture
def reports(tmp_path: Path) -> ReportFiles:
    directory = tmp_path / "raw"
    (directory / "nested").mkdir(parents=True)
    for name in (
        "ALFA-7M26.pdf",
        "Бонд_Бриф_14092026.pdf",
        "df_Uid_data_hack.csv",
        "nested/inner.pdf",
    ):
        (directory / name).write_bytes(b"%PDF-1.4")
    (tmp_path / "outside.pdf").write_bytes(b"%PDF-1.4")
    return ReportFiles(directory)


@pytest.mark.parametrize("name", ["ALFA-7M26.pdf", "Бонд_Бриф_14092026.pdf"])
def test_report_is_a_pdf_in_the_reports_directory(reports: ReportFiles, name: str) -> None:
    path = reports.path(name)
    assert path.name == name
    assert path.read_bytes() == b"%PDF-1.4"


@pytest.mark.parametrize(
    "name",
    [
        "missing.pdf",
        "df_Uid_data_hack.csv",
        "../outside.pdf",
        "nested/inner.pdf",
        "nested",
        "",
        "a\x00b.pdf",
        "a" * 300 + ".pdf",
    ],
)
def test_anything_but_a_report_is_not_found(reports: ReportFiles, name: str) -> None:
    with pytest.raises(NotFound):
        reports.path(name)
