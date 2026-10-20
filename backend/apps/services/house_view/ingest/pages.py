import zipfile
from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree

from PIL.Image import Image
from pypdf import PdfReader

DOCX_FOLDER = "word/"
DOCX_BODY = "word/document.xml"
DOCX_RELATIONS = "word/_rels/document.xml.rels"
EMBED = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"
RASTER_SUFFIXES = (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp")
IMAGE_FORMAT = "PNG"


def area(image: Image) -> int:
    return image.width * image.height


def pdf_images(path: Path) -> list[bytes]:
    images = []
    for number, page in enumerate(PdfReader(path).pages, start=1):
        decoded = [item.image for item in page.images if item.image is not None]
        if not decoded:
            raise ValueError(f"Page {number} of {path.name} has no decodable image")
        buffer = BytesIO()
        max(decoded, key=area).save(buffer, format=IMAGE_FORMAT)
        images.append(buffer.getvalue())
    return images


def docx_images(path: Path) -> list[bytes]:
    with zipfile.ZipFile(path) as archive:
        relations = ElementTree.fromstring(archive.read(DOCX_RELATIONS))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in relations}
        body = ElementTree.fromstring(archive.read(DOCX_BODY))
        names = [
            DOCX_FOLDER + targets[node.attrib[EMBED]]
            for node in body.iter()
            if EMBED in node.attrib
        ]
        return [archive.read(name) for name in names if name.lower().endswith(RASTER_SUFFIXES)]


def page_images(path: Path) -> list[bytes]:
    readers = {".pdf": pdf_images, ".docx": docx_images}
    reader = readers.get(path.suffix.lower())
    if reader is None:
        raise ValueError(f"Unsupported report format: {path.name}")
    return reader(path)
