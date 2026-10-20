import threading
from pathlib import Path
from typing import Any, Protocol

import numpy as np
import onnxruntime
from pydantic import BaseModel, ConfigDict, Field
from tokenizers import Tokenizer

from apps.services.llm.errors import ModelUnavailable
from shared.config.embedding import EMBEDDING_DIMENSION

SPEC_PATH = Path(__file__).with_name("embedder.json")
MODELS_DIR = Path(__file__).resolve().parents[3] / "models"


class ModelFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ModelFiles(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: ModelFile
    tokenizer: ModelFile


class EmbedderSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    files: ModelFiles
    max_tokens: int = Field(gt=0)
    prefix: str


class TextEmbedder(Protocol):
    spec: EmbedderSpec

    def encode(self, text: str) -> list[float]: ...


class EmbeddingDimensionMismatch(ValueError):
    pass


def load_spec(path: Path = SPEC_PATH) -> EmbedderSpec:
    return EmbedderSpec.model_validate_json(path.read_text(encoding="utf-8"))


def model_dir(spec: EmbedderSpec, models_dir: Path = MODELS_DIR) -> Path:
    return models_dir / spec.name / spec.revision


class LocalEmbedder:
    def __init__(self, spec: EmbedderSpec, directory: Path, dimension: int) -> None:
        self.spec = spec
        self._directory = directory
        self._dimension = dimension
        self._lock = threading.Lock()
        self._model: tuple[Any, Tokenizer] | None = None

    def encode(self, text: str) -> list[float]:
        session, tokenizer = self._loaded()
        encoding = tokenizer.encode(self.spec.prefix + text)
        inputs = {
            "input_ids": np.array([encoding.ids], dtype=np.int64),
            "attention_mask": np.array([encoding.attention_mask], dtype=np.int64),
            "token_type_ids": np.array([encoding.type_ids], dtype=np.int64),
        }
        pooled = session.run(None, inputs)[0][0].mean(axis=0)
        vector: list[float] = (pooled / np.linalg.norm(pooled)).tolist()
        return vector

    def _loaded(self) -> tuple[Any, Tokenizer]:
        with self._lock:
            if self._model is None:
                self._model = self._load()
            return self._model

    def _load(self) -> tuple[Any, Tokenizer]:
        weights = self._directory / self.spec.files.model.path
        vocabulary = self._directory / self.spec.files.tokenizer.path
        missing = [str(path) for path in (weights, vocabulary) if not path.is_file()]
        if missing:
            raise ModelUnavailable(
                f"embedding model files are missing: {missing}; "
                "run python -m scripts.download_embedder"
            )
        session = onnxruntime.InferenceSession(str(weights), providers=["CPUExecutionProvider"])
        size = session.get_outputs()[0].shape[-1]
        if size != self._dimension:
            raise EmbeddingDimensionMismatch(
                f"{self.spec.name} returns {size} numbers, configured {self._dimension}"
            )
        tokenizer = Tokenizer.from_file(str(vocabulary))
        tokenizer.no_padding()
        tokenizer.enable_truncation(self.spec.max_tokens)
        return session, tokenizer


def build_embedder() -> LocalEmbedder:
    spec = load_spec()
    return LocalEmbedder(spec, model_dir(spec), EMBEDDING_DIMENSION)
