from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from shared.config.settings import Settings

MODELS_PATH = Path(__file__).with_name("models.yaml")


class UnknownTask(LookupError):
    pass


class ModelNotAllowed(ValueError):
    pass


class ModelsFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    models: frozenset[str] = Field(min_length=1)
    reasoning_off_tasks: frozenset[str]
    interactive_tasks: frozenset[str]


def reject_unknown(tasks: frozenset[str], routes: dict[str, str], setting: str) -> None:
    unknown = sorted(tasks - set(routes))
    if unknown:
        raise UnknownTask(f"{setting} names unknown tasks: {unknown}")


class ModelCatalog:
    def __init__(
        self,
        allowed: frozenset[str],
        routes: dict[str, str],
        reasoning_off: frozenset[str],
        timeouts: dict[str, float],
    ) -> None:
        foreign = sorted(set(routes.values()) - allowed)
        if foreign:
            raise ModelNotAllowed(f"models outside the allow-list: {foreign}")
        reject_unknown(reasoning_off, routes, "reasoning_off_tasks")
        untimed = sorted(set(routes) - set(timeouts))
        if untimed:
            raise UnknownTask(f"no timeout is set for tasks: {untimed}")
        self._routes = routes
        self._reasoning_off = reasoning_off
        self._timeouts = timeouts

    def route(self, task: str) -> str:
        model = self._routes.get(task)
        if model is None:
            raise UnknownTask(f"no model is routed for task {task!r}")
        return model

    def reasoning(self, task: str) -> bool:
        return task not in self._reasoning_off

    def timeout(self, task: str) -> float:
        seconds = self._timeouts.get(task)
        if seconds is None:
            raise UnknownTask(f"no timeout is set for task {task!r}")
        return seconds


def load_models(path: Path) -> ModelsFile:
    return ModelsFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def build_catalog(
    settings: Settings,
    allowed: frozenset[str],
    reasoning_off: frozenset[str],
    interactive: frozenset[str],
) -> ModelCatalog:
    routes = {
        "annotate": settings.MODEL_ANNOTATE,
        "extract": settings.MODEL_EXTRACT,
        "interpret": settings.MODEL_INTERPRET,
        "critic": settings.MODEL_CRITIC,
        "followup": settings.MODEL_FOLLOWUP,
    }
    reject_unknown(interactive, routes, "interactive_tasks")
    timeouts = {
        task: settings.LLM_INTERACTIVE_TIMEOUT_SECONDS
        if task in interactive
        else settings.LLM_TIMEOUT_SECONDS
        for task in routes
    }
    return ModelCatalog(allowed, routes, reasoning_off, timeouts)
