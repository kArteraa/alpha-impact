import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from apps.services.house_view.ingest.pages import page_images

COLORS = ((200, 30, 30), (30, 200, 30), (30, 30, 200))


def dominant(image: bytes) -> tuple[int, ...]:
    with Image.open(BytesIO(image)) as picture:
        pixel = picture.convert("RGB").getpixel((5, 5))
    assert isinstance(pixel, tuple)
    return tuple(round(channel / 50) for channel in pixel)


def expected(color: tuple[int, int, int]) -> tuple[int, ...]:
    return tuple(round(channel / 50) for channel in color)


def png(color: tuple[int, int, int]) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (40, 60), color).save(buffer, format="PNG")
    return buffer.getvalue()


def test_pdf_pages_come_out_in_order(tmp_path: Path) -> None:
    pages = [Image.new("RGB", (40, 60), color) for color in COLORS]
    path = tmp_path / "report.pdf"
    pages[0].save(path, save_all=True, append_images=pages[1:])

    images = page_images(path)

    assert [dominant(image) for image in images] == [expected(color) for color in COLORS]


def test_docx_media_comes_out_in_natural_order(tmp_path: Path) -> None:
    path = tmp_path / "report.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", "<w:document/>")
        archive.writestr("word/media/image10.png", png(COLORS[2]))
        archive.writestr("word/media/image2.png", png(COLORS[1]))
        archive.writestr("word/media/image1.png", png(COLORS[0]))

    images = page_images(path)

    assert [dominant(image) for image in images] == [expected(color) for color in COLORS]


def test_unknown_format_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "report.txt"
    path.write_text("text", encoding="utf-8")

    with pytest.raises(ValueError, match="report.txt"):
        page_images(path)
