from collections import Counter
from pathlib import Path
from typing import Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, field_validator, model_validator

from shared.contracts.schemas import ActionContext

RULES_PATH = Path(__file__).with_name("rules.yaml")
ACTION_TYPES = frozenset(TypeAdapter(ActionContext).json_schema()["discriminator"]["mapping"])


class Vocabulary(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    features: dict[str, str]
    flags: dict[str, str]
    claims: dict[str, str]


class Rule(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str
    product: str
    reason: str
    action_types: list[str] = Field(min_length=1)
    flags: list[str]
    claims: list[str]

    @field_validator("action_types")
    @classmethod
    def known_action_types(cls, action_types: list[str]) -> list[str]:
        unknown = set(action_types) - ACTION_TYPES
        if unknown:
            raise ValueError(f"unknown action types: {sorted(unknown)}")
        return action_types


class Exclusion(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    features: dict[str, str]


class Catalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    vocabulary: Vocabulary
    exclude: Exclusion
    rules: list[Rule]

    @field_validator("rules")
    @classmethod
    def unique_rule_ids(cls, rules: list[Rule]) -> list[Rule]:
        duplicates = [rule_id for rule_id, n in Counter(r.id for r in rules).items() if n > 1]
        if duplicates:
            raise ValueError(f"duplicate rule ids: {sorted(duplicates)}")
        return rules

    @model_validator(mode="after")
    def names_from_vocabulary(self) -> Self:
        _require_known("features", set(self.exclude.features), self.vocabulary.features)
        for rule in self.rules:
            _require_known(f"{rule.id} flags", set(rule.flags), self.vocabulary.flags)
            _require_known(f"{rule.id} claims", set(rule.claims), self.vocabulary.claims)
        return self


def load_catalog(path: Path) -> Catalog:
    return Catalog.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def _require_known(where: str, names: set[str], vocabulary: dict[str, str]) -> None:
    unknown = names - set(vocabulary)
    if unknown:
        raise ValueError(f"{where} not in vocabulary: {sorted(unknown)}")
