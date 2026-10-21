import shutil
import sys
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont

from apps.services.house_view.ingest import ocr
from apps.services.house_view.ingest.config import load_config
from apps.services.house_view.ingest.ocr import TesseractOcr


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")
def test_tesseract_reads_printed_numbers() -> None:
    picture = Image.new("RGB", (600, 160), "white")
    ImageDraw.Draw(picture).text(
        (20, 40), "rate 14.25%", fill="black", font=ImageFont.load_default(56)
    )
    buffer = BytesIO()
    picture.save(buffer, format="PNG")
    config = load_config()

    text = TesseractOcr(config.ocr_languages, config.ocr_timeout_seconds).read(buffer.getvalue())

    assert "14.25" in text


def test_failed_tesseract_reports_its_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ocr, "TESSERACT", sys.executable)
    monkeypatch.chdir(tmp_path)

    with pytest.raises(RuntimeError, match="tesseract failed: .*stdin"):
        TesseractOcr("rus", 10).read(b"image")


def test_hung_tesseract_is_stopped_by_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(ocr, "TESSERACT", sys.executable)
    monkeypatch.chdir(tmp_path)
    (tmp_path / "stdin").write_text("import time\ntime.sleep(10)\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="did not finish in 0.5 s"):
        TesseractOcr("rus", 0.5).read(b"image")
