import shutil
from io import BytesIO

import pytest
from PIL import Image, ImageDraw, ImageFont

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

    text = TesseractOcr(load_config().ocr_languages).read(buffer.getvalue())

    assert "14.25" in text
