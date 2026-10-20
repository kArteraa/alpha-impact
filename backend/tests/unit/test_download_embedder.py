import hashlib
import io
import json
from pathlib import Path

import pytest

from apps.services.llm.embedder import MODELS_DIR, SPEC_PATH, load_spec, model_dir
from scripts import download_embedder

PAYLOAD = b"onnx weights"
REVISION = "a" * 40
BASE_URL = f"https://huggingface.co/org/model/resolve/{REVISION}"


def write_spec(path: Path, sha256: str) -> Path:
    spec = {
        "name": "org/model",
        "revision": REVISION,
        "files": {
            "model": {"path": "onnx/model.onnx", "sha256": sha256},
            "tokenizer": {"path": "onnx/tokenizer.json", "sha256": sha256},
        },
        "max_tokens": 512,
        "prefix": "query: ",
    }
    path.write_text(json.dumps(spec), encoding="utf-8")
    return path


class Source:
    def __init__(self, payload: bytes = PAYLOAD, broken: bool = False) -> None:
        self.payload = payload
        self.broken = broken
        self.urls: list[str] = []

    def __call__(self, url: str, timeout: float) -> io.BytesIO:
        self.urls.append(url)
        if self.broken:
            return BrokenStream(self.payload)
        return io.BytesIO(self.payload)


class BrokenStream(io.BytesIO):
    def read(self, size: int | None = -1) -> bytes:
        raise ConnectionResetError("connection dropped")


@pytest.fixture
def source(monkeypatch: pytest.MonkeyPatch) -> Source:
    fake = Source()
    monkeypatch.setattr(download_embedder, "urlopen", fake)
    return fake


def files_under(directory: Path) -> list[Path]:
    return [path for path in directory.rglob("*") if path.is_file()]


def test_pinned_files_land_in_the_revision_directory(tmp_path: Path, source: Source) -> None:
    spec = write_spec(tmp_path / "embedder.json", hashlib.sha256(PAYLOAD).hexdigest())
    directory = download_embedder.download(spec, tmp_path / "models")
    assert directory == tmp_path / "models" / "org" / "model" / REVISION
    assert (directory / "onnx" / "model.onnx").read_bytes() == PAYLOAD
    assert (directory / "onnx" / "tokenizer.json").read_bytes() == PAYLOAD
    assert source.urls == [f"{BASE_URL}/onnx/model.onnx", f"{BASE_URL}/onnx/tokenizer.json"]


def test_downloaded_files_are_not_fetched_again(tmp_path: Path, source: Source) -> None:
    spec = write_spec(tmp_path / "embedder.json", hashlib.sha256(PAYLOAD).hexdigest())
    download_embedder.download(spec, tmp_path / "models")
    download_embedder.download(spec, tmp_path / "models")
    assert len(source.urls) == 2


def test_file_with_a_foreign_hash_is_not_kept(tmp_path: Path, source: Source) -> None:
    spec = write_spec(tmp_path / "embedder.json", "0" * 64)
    with pytest.raises(ValueError, match="sha256"):
        download_embedder.download(spec, tmp_path / "models")
    assert files_under(tmp_path / "models") == []


def test_dropped_download_leaves_no_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(download_embedder, "urlopen", Source(broken=True))
    spec = write_spec(tmp_path / "embedder.json", hashlib.sha256(PAYLOAD).hexdigest())
    with pytest.raises(ConnectionResetError):
        download_embedder.download(spec, tmp_path / "models")
    assert files_under(tmp_path / "models") == []


def test_model_lands_where_the_gateway_reads_it() -> None:
    raw = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    assert download_embedder.MODELS_DIR == MODELS_DIR
    assert download_embedder.target_dir(raw, MODELS_DIR) == model_dir(load_spec())
