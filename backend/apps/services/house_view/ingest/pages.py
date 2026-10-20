import re
import zipfile
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

MEDIA_PREFIX = "word/media/"
RASTER_SUFFIXES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
IMAGE_FORMAT = "PNG"


def natural_key(name: str) -> tuple[int, str]:
    numbers = re.findall(r"\d+", name)
    return (int(numbers[-1]) if numbers else 0, name)


def pdf_images(path: Path) -> list[bytes]:
    images = []
    for number, page in enumerate(PdfReader(path).pages, start=1):
        image = page.images[0].image if page.images else None
        if image is None:
            raise ValueError(f"Page {number} of {path.name} has no decodable image")
        buffer = BytesIO()
        image.save(buffer, format=IMAGE_FORMAT)
        images.append(buffer.getvalue())
    return images


def docx_images(path: Path) -> list[bytes]:
    with zipfile.ZipFile(path) as archive:
        names = [
            name
            for name in archive.namelist()
            if name.startswith(MEDIA_PREFIX) and name.lower().endswith(RASTER_SUFFIXES)
        ]
        return [archive.read(name) for name in sorted(names, key=natural_key)]


def page_images(path: Path) -> list[bytes]:
    readers = {".pdf": pdf_images, ".docx": docx_images}
    reader = readers.get(path.suffix.lower())
    if reader is None:
        raise ValueError(f"Unsupported report format: {path.name}")
    return reader(path)
