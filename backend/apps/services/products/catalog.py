from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field

RULES_PATH = Path(__file__).with_name("rules.yaml")


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    product: str
    reason: str
    action_types: list[str] = Field(min_length=1)
    flags: list[str]
    claims: list[str]


class Exclusion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    features: dict[str, str]


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    exclude: Exclusion
    rules: list[Rule]


def load_catalog(path: Path) -> Catalog:
    return Catalog.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
