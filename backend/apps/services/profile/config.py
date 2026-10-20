from pathlib import Path

import yaml
from pydantic import BaseModel, model_validator

from shared.config.factors import FACTORS

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
    confidence: Confidence
    products: dict[str, str]
    foreign_ownership: frozenset[str]
    state_ownership: frozenset[str]
    workers_scale: dict[str, float]
    countries_cap: int
    exposures: dict[str, ExposureRule]

    @model_validator(mode="after")
    def exposures_cover_factors(self) -> "ProfileConfig":
        if tuple(self.exposures) != FACTORS:
            raise ValueError(f"exposures must list the shared factors in order: {FACTORS}")
        return self


def load_config() -> ProfileConfig:
    return ProfileConfig.model_validate(
        yaml.safe_load((CONFIG_DIR / "config.yaml").read_text(encoding="utf-8"))
    )
