import pytest

from apps.services.llm.embedder import LocalEmbedder, load_spec, model_dir
from shared.config.embedding import EMBEDDING_DIMENSION


@pytest.fixture(scope="session")
def e5() -> LocalEmbedder:
    spec = load_spec()
    return LocalEmbedder(spec, model_dir(spec), EMBEDDING_DIMENSION)
