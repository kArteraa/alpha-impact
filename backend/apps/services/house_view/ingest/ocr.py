import subprocess
from typing import Protocol

TESSERACT = "tesseract"


class Ocr(Protocol):
    def read(self, image: bytes) -> str: ...


class TesseractOcr:
    def __init__(self, languages: str) -> None:
        self._languages = languages

    def read(self, image: bytes) -> str:
        result = subprocess.run(
            [TESSERACT, "stdin", "stdout", "-l", self._languages],
            input=image,
            capture_output=True,
            check=True,
        )
        return result.stdout.decode("utf-8")
