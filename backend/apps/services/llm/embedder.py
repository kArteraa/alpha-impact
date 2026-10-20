import threading
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime
from pydantic import BaseModel, ConfigDict, Field
from tokenizers import Tokenizer

from apps.services.llm.errors import ModelUnavailable

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
        self._model: tuple[Any, Any] | None = None

    def encode(self, text: str) -> list[float]:
        session, tokenizer = self._loaded()
        ids = np.array([tokenizer.encode(self.spec.prefix + text).ids], dtype=np.int64)
        inputs = {
            "input_ids": ids,
            "attention_mask": np.ones_like(ids),
            "token_type_ids": np.zeros_like(ids),
        }
        hidden = session.run(None, inputs)[0][0]
        pooled = hidden.mean(axis=0)
        vector: list[float] = (pooled / np.linalg.norm(pooled)).tolist()
        if len(vector) != self._dimension:
            raise EmbeddingDimensionMismatch(
                f"{self.spec.name} returns {len(vector)} numbers, configured {self._dimension}"
            )
        return vector

    def _loaded(self) -> tuple[Any, Any]:
        with self._lock:
            if self._model is None:
                self._model = self._load()
            return self._model

    def _load(self) -> tuple[Any, Any]:
        weights = self._directory / self.spec.files.model.path
        vocabulary = self._directory / self.spec.files.tokenizer.path
        missing = [str(path) for path in (weights, vocabulary) if not path.is_file()]
        if missing:
            raise ModelUnavailable(
                f"embedding model files are missing: {missing}; "
                "run python -m scripts.download_embedder"
            )
        tokenizer = Tokenizer.from_file(str(vocabulary))
        tokenizer.no_padding()
        tokenizer.enable_truncation(self.spec.max_tokens)
        session = onnxruntime.InferenceSession(str(weights), providers=["CPUExecutionProvider"])
        return session, tokenizer
