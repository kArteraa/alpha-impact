from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

from shared.config.settings import Settings

MODELS_PATH = Path(__file__).with_name("models.yaml")
TOKENS_PER_PRICE = 1_000_000


class UnknownTask(LookupError):
    pass


class ModelNotAllowed(ValueError):
    pass


class ModelPrice(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    input_rub_per_1m: float = Field(gt=0)
    output_rub_per_1m: float = Field(gt=0)


class ModelsFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    models: dict[str, ModelPrice] = Field(min_length=1)
    reasoning_off_tasks: frozenset[str]


class ModelCatalog:
    def __init__(
        self,
        prices: dict[str, ModelPrice],
        routes: dict[str, str],
        embedding_model: str,
        reasoning_off: frozenset[str],
    ) -> None:
        foreign = sorted({*routes.values(), embedding_model} - set(prices))
        if foreign:
            raise ModelNotAllowed(f"models outside the allow-list: {foreign}")
        unknown = sorted(reasoning_off - set(routes))
        if unknown:
            raise UnknownTask(f"reasoning is switched off for unknown tasks: {unknown}")
        self._prices = prices
        self._routes = routes
        self._reasoning_off = reasoning_off
        self.embedding_model = embedding_model

    def route(self, task: str) -> str:
        model = self._routes.get(task)
        if model is None:
            raise UnknownTask(f"no model is routed for task {task!r}")
        return model

    def reasoning(self, task: str) -> bool:
        return task not in self._reasoning_off

    def cost_rub(self, model: str, tokens_in: int, tokens_out: int) -> float:
        price = self._prices[model]
        spent = tokens_in * price.input_rub_per_1m + tokens_out * price.output_rub_per_1m
        return spent / TOKENS_PER_PRICE


def load_models(path: Path) -> ModelsFile:
    return ModelsFile.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def build_catalog(
    settings: Settings,
    prices: dict[str, ModelPrice],
    reasoning_off: frozenset[str],
) -> ModelCatalog:
    routes = {
        "annotate": settings.MODEL_ANNOTATE,
        "extract": settings.MODEL_EXTRACT,
        "interpret": settings.MODEL_INTERPRET,
        "critic": settings.MODEL_CRITIC,
        "followup": settings.MODEL_FOLLOWUP,
    }
    return ModelCatalog(prices, routes, settings.MODEL_EMBED, reasoning_off)
