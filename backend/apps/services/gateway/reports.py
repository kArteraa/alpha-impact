from pathlib import Path

from shared.contracts.errors import NotFound

REPORTS_DIR = Path(__file__).resolve().parents[3] / "data" / "raw"
REPORT_SUFFIX = ".pdf"


class ReportFiles:
    def __init__(self, directory: Path) -> None:
        self.directory = directory.resolve()

    def path(self, name: str) -> Path:
        candidate = (self.directory / name).resolve()
        if (
            candidate.parent != self.directory
            or candidate.suffix != REPORT_SUFFIX
            or not candidate.is_file()
        ):
            raise NotFound(f"Unknown report {name}")
        return candidate
