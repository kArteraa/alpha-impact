import subprocess
from typing import Protocol

TESSERACT = "tesseract"


class Ocr(Protocol):
    def read(self, image: bytes) -> str: ...


class TesseractOcr:
    def __init__(self, languages: str, timeout_seconds: float) -> None:
        self._languages = languages
        self._timeout_seconds = timeout_seconds

    def read(self, image: bytes) -> str:
        try:
            result = subprocess.run(
                [TESSERACT, "stdin", "stdout", "-l", self._languages],
                input=image,
                capture_output=True,
                check=False,
                timeout=self._timeout_seconds,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError(f"tesseract did not finish in {self._timeout_seconds} s") from error
        if result.returncode != 0:
            raise RuntimeError(f"tesseract failed: {result.stderr.decode('utf-8', 'replace')}")
        return result.stdout.decode("utf-8")
