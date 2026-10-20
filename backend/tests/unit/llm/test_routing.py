from pathlib import Path

import pytest

from apps.services.llm.catalog import (
    MODELS_PATH,
    ModelCatalog,
    ModelNotAllowed,
    UnknownTask,
    build_catalog,
    load_prices,
)
from shared.config.settings import Settings
from tests.unit.llm.fakes import EMBEDDING_MODEL, PRICES, ROUTES

CASE_ALLOW_LIST = {
    "google/gemma-4-26b-a4b-it",
    "z-ai/glm-5.3-flash",
    "qwen/qwen3.6-35b-a3b",
    "deepseek/deepseek-v4.1-flash",
    "qwen/qwen3-vl-30b-a3b-instruct",
    "moonshotai/kimi-k2.6",
}


@pytest.mark.parametrize(("task", "model"), ROUTES.items())
def test_settings_route_each_task_to_its_model(
    settings_env: dict[str, str], task: str, model: str
) -> None:
    catalog = build_catalog(Settings(_env_file=None), load_prices(MODELS_PATH))
    assert catalog.route(task) == model


def test_embedding_model_comes_from_settings(settings_env: dict[str, str]) -> None:
    catalog = build_catalog(Settings(_env_file=None), load_prices(MODELS_PATH))
    assert catalog.embedding_model == settings_env["MODEL_EMBED"]


def test_unknown_task_is_rejected() -> None:
    with pytest.raises(UnknownTask, match="summarize"):
        ModelCatalog(PRICES, ROUTES, EMBEDDING_MODEL).route("summarize")


def test_model_outside_allow_list_fails_at_load() -> None:
    with pytest.raises(ModelNotAllowed, match="gpt-4o"):
        ModelCatalog(PRICES, {**ROUTES, "interpret": "gpt-4o"}, EMBEDDING_MODEL)


def test_embedding_model_outside_allow_list_fails_at_load() -> None:
    with pytest.raises(ModelNotAllowed, match="text-embedding-3"):
        ModelCatalog(PRICES, ROUTES, "text-embedding-3")


def test_settings_with_foreign_model_fail_at_load(
    settings_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MODEL_CRITIC", "claude-opus")
    with pytest.raises(ModelNotAllowed, match="claude-opus"):
        build_catalog(Settings(_env_file=None), load_prices(MODELS_PATH))


def test_models_file_lists_the_case_allow_list_and_one_embedding_model() -> None:
    prices = load_prices(MODELS_PATH)
    assert CASE_ALLOW_LIST <= set(prices)
    assert len(set(prices) - CASE_ALLOW_LIST) == 1


def test_cost_is_priced_per_million_tokens() -> None:
    catalog = ModelCatalog(PRICES, ROUTES, EMBEDDING_MODEL)
    assert catalog.cost_rub("z-ai/glm-5.3-flash", 1_000_000, 0) == pytest.approx(100.0)
    assert catalog.cost_rub("z-ai/glm-5.3-flash", 1000, 500) == pytest.approx(0.1 + 0.15)


def test_models_file_without_prices_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "models.yaml"
    path.write_text("models:\n  z-ai/glm-5.3-flash: {input_rub_per_1m: 1}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="output_rub_per_1m"):
        load_prices(path)
