import hashlib
import json
from pathlib import Path
from typing import Any
from urllib.request import urlopen

BACKEND = Path(__file__).resolve().parents[1]
SPEC_PATH = BACKEND / "apps" / "services" / "llm" / "embedder.json"
MODELS_DIR = BACKEND / "models"
SOURCE_URL = "https://huggingface.co/{name}/resolve/{revision}/{path}"
TIMEOUT_SECONDS = 60
CHUNK_BYTES = 1 << 20


def target_dir(spec: dict[str, Any], models_dir: Path) -> Path:
    return models_dir / spec["name"] / spec["revision"]


def fetch(url: str, target: Path, sha256: str) -> None:
    partial = target.with_name(target.name + ".part")
    digest = hashlib.sha256()
    try:
        with urlopen(url, timeout=TIMEOUT_SECONDS) as response, partial.open("wb") as file:
            while chunk := response.read(CHUNK_BYTES):
                digest.update(chunk)
                file.write(chunk)
        if digest.hexdigest() != sha256:
            raise ValueError(f"{url} has sha256 {digest.hexdigest()}, expected {sha256}")
        partial.replace(target)
    finally:
        partial.unlink(missing_ok=True)


def download(spec_path: Path = SPEC_PATH, models_dir: Path = MODELS_DIR) -> Path:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    directory = target_dir(spec, models_dir)
    for file in spec["files"].values():
        target = directory / file["path"]
        if target.is_file():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        url = SOURCE_URL.format(name=spec["name"], revision=spec["revision"], path=file["path"])
        fetch(url, target, file["sha256"])
    return directory


if __name__ == "__main__":
    print(download())
