import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from pypdf import PdfReader, PdfWriter

from apps.services.house_view.ingest.pages import page_images

COLORS = ((200, 30, 30), (30, 200, 30), (30, 30, 200))
PACKAGE = "http://schemas.openxmlformats.org/package/2006/relationships"
WORD = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
DRAWING = "http://schemas.openxmlformats.org/drawingml/2006/main"
RELATIONSHIPS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"


def dominant(image: bytes) -> tuple[int, ...]:
    with Image.open(BytesIO(image)) as picture:
        pixel = picture.convert("RGB").getpixel((5, 5))
    assert isinstance(pixel, tuple)
    return expected(pixel)


def expected(color: tuple[int, ...]) -> tuple[int, ...]:
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


def test_pdf_page_takes_its_largest_image(tmp_path: Path) -> None:
    logo, scan = Image.new("RGB", (10, 10), COLORS[0]), Image.new("RGB", (40, 60), COLORS[1])
    source = tmp_path / "source.pdf"
    logo.save(source, save_all=True, append_images=[scan])
    writer = PdfWriter(clone_from=source)
    writer.pages[0].merge_page(writer.pages[1])
    writer.remove_page(1)
    path = tmp_path / "report.pdf"
    writer.write(path)
    assert len(PdfReader(path).pages[0].images) == 2

    images = page_images(path)

    assert [dominant(image) for image in images] == [expected(COLORS[1])]


def test_pdf_page_without_image_is_rejected(tmp_path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    path = tmp_path / "blank.pdf"
    writer.write(path)

    with pytest.raises(ValueError, match="Page 1 of blank.pdf"):
        page_images(path)


def test_docx_images_come_out_in_document_order(tmp_path: Path) -> None:
    targets = {
        "rId7": ("media/image3.png", png(COLORS[0])),
        "rId9": ("media/image4.emf", b"emf"),
        "rId8": ("media/image1.png", png(COLORS[1])),
        "rId10": ("media/image2.png", png(COLORS[2])),
    }
    relations = "".join(
        f'<Relationship Id="{rid}" Target="{target}"/>' for rid, (target, _) in targets.items()
    )
    blips = "".join(f'<a:blip r:embed="{rid}"/>' for rid in targets)
    path = tmp_path / "report.docx"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr(
            "word/_rels/document.xml.rels",
            f'<Relationships xmlns="{PACKAGE}">{relations}</Relationships>',
        )
        archive.writestr(
            "word/document.xml",
            f'<w:document xmlns:w="{WORD}" xmlns:a="{DRAWING}" xmlns:r="{RELATIONSHIPS}">'
            f"<w:body>{blips}</w:body></w:document>",
        )
        for target, content in targets.values():
            archive.writestr(f"word/{target}", content)

    images = page_images(path)

    assert [dominant(image) for image in images] == [expected(color) for color in COLORS]


def test_unknown_format_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "report.txt"
    path.write_text("text", encoding="utf-8")

    with pytest.raises(ValueError, match="report.txt"):
        page_images(path)
