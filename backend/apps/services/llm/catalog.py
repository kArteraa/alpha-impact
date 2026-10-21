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

    models: list[str] = Field(min_length=1)


class ModelCatalog:
    def __init__(self, allowed: frozenset[str], routes: dict[str, str]) -> None:
        foreign = sorted(set(routes.values()) - allowed)
        if foreign:
            raise ModelNotAllowed(f"models outside the allow-list: {foreign}")
        self._routes = routes

    def route(self, task: str) -> str:
        model = self._routes.get(task)
        if model is None:
            raise UnknownTask(f"no model is routed for task {task!r}")
        return model


def load_models(path: Path) -> frozenset[str]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return frozenset(ModelsFile.model_validate(raw).models)


def build_catalog(settings: Settings, allowed: frozenset[str]) -> ModelCatalog:
    routes = {
        "annotate": settings.MODEL_ANNOTATE,
        "extract": settings.MODEL_EXTRACT,
        "interpret": settings.MODEL_INTERPRET,
        "critic": settings.MODEL_CRITIC,
        "followup": settings.MODEL_FOLLOWUP,
    }
    return ModelCatalog(allowed, routes)
