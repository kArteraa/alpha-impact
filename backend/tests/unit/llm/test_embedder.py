import json
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from apps.services.llm.embedder import (
    SPEC_PATH,
    EmbeddingDimensionMismatch,
    LocalEmbedder,
    load_spec,
    model_dir,
)
from apps.services.llm.errors import ModelUnavailable
from shared.config.embedding import EMBEDDING_DIMENSION
from shared.contracts.errors import DomainError


def cosine(left: list[float], right: list[float]) -> float:
    return math.fsum(a * b for a, b in zip(left, right, strict=True))


def test_vector_has_the_configured_dimension_and_unit_length(e5: LocalEmbedder) -> None:
    vector = e5.encode("Банк России снизил ключевую ставку")
    assert len(vector) == EMBEDDING_DIMENSION
    assert math.fsum(x * x for x in vector) == pytest.approx(1.0, abs=1e-5)


def test_paraphrase_is_closer_than_unrelated_text(e5: LocalEmbedder) -> None:
    news = e5.encode("Центробанк понизил ключевую ставку")
    paraphrase = e5.encode("Банк России снизил ключевую ставку")
    unrelated = e5.encode("Рецепт яблочного пирога с корицей")
    assert cosine(news, paraphrase) > cosine(news, unrelated)


def test_text_longer_than_the_model_limit_is_encoded(e5: LocalEmbedder) -> None:
    assert len(e5.encode("ключевая ставка " * 2000)) == EMBEDDING_DIMENSION


def test_missing_model_files_make_the_model_unavailable(tmp_path: Path) -> None:
    embedder = LocalEmbedder(load_spec(), tmp_path, EMBEDDING_DIMENSION)
    with pytest.raises(ModelUnavailable, match="download_embedder") as raised:
        embedder.encode("ставка")
    assert isinstance(raised.value, DomainError)


def test_dimension_other_than_the_model_output_is_rejected() -> None:
    spec = load_spec()
    embedder = LocalEmbedder(spec, model_dir(spec), EMBEDDING_DIMENSION + 1)
    with pytest.raises(EmbeddingDimensionMismatch, match=str(EMBEDDING_DIMENSION + 1)):
        embedder.encode("ставка")


def test_spec_pins_e5_small_by_revision() -> None:
    spec = load_spec()
    assert spec.name == "intfloat/multilingual-e5-small"
    assert spec.prefix == "query: "
    assert model_dir(spec).parts[-3:] == ("intfloat", "multilingual-e5-small", spec.revision)


@pytest.mark.parametrize(
    ("field", "value"),
    [("revision", "main"), ("files", {"model": {"path": "onnx/model.onnx", "sha256": "x"}})],
)
def test_spec_without_pinned_revision_and_hashes_is_rejected(
    tmp_path: Path, field: str, value: object
) -> None:
    raw = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    path = tmp_path / "embedder.json"
    path.write_text(json.dumps({**raw, field: value}), encoding="utf-8")
    with pytest.raises(ValidationError, match=field):
        load_spec(path)
