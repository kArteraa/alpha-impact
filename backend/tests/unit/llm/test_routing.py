from pathlib import Path

import pytest

from apps.services.llm.catalog import (
    MODELS_PATH,
    ModelCatalog,
    ModelNotAllowed,
    UnknownTask,
    build_catalog,
    load_models,
)
from shared.config.settings import Settings
from tests.unit.llm.fakes import ALLOWED, ROUTES

CASE_ALLOW_LIST = {
    "google/gemma-4-26b-a4b-it",
    "z-ai/glm-5.3-flash",
    "qwen/qwen3.6-35b-a3b",
    "deepseek/deepseek-v4.1-flash",
    "qwen/qwen3-vl-30b-a3b-instruct",
    "moonshotai/kimi-k2.6",
}


def catalog_from_file() -> ModelCatalog:
    models = load_models(MODELS_PATH)
    return build_catalog(Settings(_env_file=None), models.models, models.reasoning_off_tasks)


@pytest.mark.parametrize(("task", "model"), ROUTES.items())
def test_settings_route_each_task_to_its_model(
    settings_env: dict[str, str], task: str, model: str
) -> None:
    assert catalog_from_file().route(task) == model


def test_unknown_task_is_rejected() -> None:
    with pytest.raises(UnknownTask, match="summarize"):
        ModelCatalog(ALLOWED, ROUTES, frozenset()).route("summarize")


def test_model_outside_allow_list_fails_at_load() -> None:
    with pytest.raises(ModelNotAllowed, match="gpt-4o"):
        ModelCatalog(ALLOWED, {**ROUTES, "interpret": "gpt-4o"}, frozenset())


def test_settings_with_foreign_model_fail_at_load(
    settings_env: dict[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("MODEL_CRITIC", "claude-opus")
    with pytest.raises(ModelNotAllowed, match="claude-opus"):
        catalog_from_file()


def test_models_file_lists_exactly_the_case_allow_list() -> None:
    assert load_models(MODELS_PATH).models == CASE_ALLOW_LIST


def test_empty_models_file_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "models.yaml"
    path.write_text("models: []\nreasoning_off_tasks: []\n", encoding="utf-8")
    with pytest.raises(ValueError, match="models"):
        load_models(path)


def test_models_file_turns_reasoning_off_only_for_routed_tasks() -> None:
    reasoning_off = load_models(MODELS_PATH).reasoning_off_tasks
    assert reasoning_off == {"extract"}
    catalog = ModelCatalog(ALLOWED, ROUTES, reasoning_off)
    assert catalog.reasoning("extract") is False
    assert catalog.reasoning("interpret") is True


def test_reasoning_switch_for_unknown_task_is_rejected() -> None:
    with pytest.raises(UnknownTask, match="summarize"):
        ModelCatalog(ALLOWED, ROUTES, frozenset({"summarize"}))
