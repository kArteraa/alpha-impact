from pathlib import Path

from shared.contracts.errors import NotFound

REPORT_SUFFIX = ".pdf"


class ReportFiles:
    def __init__(self, directory: Path) -> None:
        self.directory = directory.resolve()

    def path(self, name: str) -> Path:
        try:
            candidate = (self.directory / name).resolve()
            found = (
                candidate.parent == self.directory
                and candidate.suffix == REPORT_SUFFIX
                and candidate.is_file()
            )
        except (OSError, ValueError) as error:
            raise NotFound(f"Unknown report {name}") from error
        if not found:
            raise NotFound(f"Unknown report {name}")
        return candidate
