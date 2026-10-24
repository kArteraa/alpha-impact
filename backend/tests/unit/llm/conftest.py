import pytest

from apps.services.llm.embedder import LocalEmbedder, build_embedder


@pytest.fixture(scope="session")
def e5() -> LocalEmbedder:
    return build_embedder()
