from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

CONFIG_DIR = Path(__file__).resolve().parent


class Confidence(BaseModel):
    bank: float
    inferred: float
    user: float


class ExposureRule(BaseModel):
    products: dict[str, float] = {}
    industries: dict[str, float] = {}
    importer: float = 0.0
    per_country: float = 0.0
    foreign_owned: float = 0.0
    state_owned: float = 0.0
    workers: float = 0.0


class ProfileConfig(BaseModel):
    companies_file: str
    min_revenue_rub: float
    confidence: Confidence
    products: dict[str, str]
    foreign_ownership: frozenset[str]
    state_ownership: frozenset[str]
    workers_scale: dict[str, float]
    countries_cap: int
    exposures: dict[str, ExposureRule]
    industries: dict[str, str]


def read_yaml(name: str) -> dict[str, Any]:
    content: dict[str, Any] = yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))
    return content


def load_config() -> ProfileConfig:
    return ProfileConfig.model_validate(
        {**read_yaml("config.yaml"), "industries": read_yaml("industries.yaml")}
    )
