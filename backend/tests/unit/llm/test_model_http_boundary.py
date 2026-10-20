from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
GATEWAY = ROOT / "apps" / "services" / "llm"
MODEL_API_MARKERS = ("LLM_API_BASE", "LLM_API_KEY", "/chat/completions", "/embeddings")


def sources_outside_gateway() -> list[Path]:
    roots = [ROOT / "apps", ROOT / "scripts"]
    files = [path for root in roots for path in root.rglob("*.py")]
    return [path for path in files if GATEWAY not in path.parents] + [ROOT / "main.py"]


def model_api_mentions(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    return [marker for marker in MODEL_API_MARKERS if marker in text]


def test_only_llm_service_reaches_the_model_api() -> None:
    offenders = {
        str(path.relative_to(ROOT)): found
        for path in sources_outside_gateway()
        if (found := model_api_mentions(path))
    }
    assert offenders == {}


@pytest.mark.parametrize("marker", MODEL_API_MARKERS)
def test_detector_flags_each_marker(tmp_path: Path, marker: str) -> None:
    path = tmp_path / "rogue.py"
    path.write_text(f'URL = "{marker}"\n', encoding="utf-8")
    assert model_api_mentions(path) == [marker]


def test_gateway_itself_holds_the_model_api() -> None:
    found = {marker for path in GATEWAY.rglob("*.py") for marker in model_api_mentions(path)}
    assert found == set(MODEL_API_MARKERS)
