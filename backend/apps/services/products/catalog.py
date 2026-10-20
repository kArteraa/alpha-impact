from pathlib import Path
from typing import get_args

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from shared.contracts.schemas import ActionContext

RULES_PATH = Path(__file__).with_name("rules.yaml")
ACTION_TYPES = frozenset(
    context.model_fields["type"].default for context in get_args(get_args(ActionContext)[0])
)


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

    exclude: Exclusion
    rules: list[Rule]

    @field_validator("rules")
    @classmethod
    def unique_rule_ids(cls, rules: list[Rule]) -> list[Rule]:
        ids = [rule.id for rule in rules]
        duplicates = {rule_id for rule_id in ids if ids.count(rule_id) > 1}
        if duplicates:
            raise ValueError(f"duplicate rule ids: {sorted(duplicates)}")
        return rules


def load_catalog(path: Path) -> Catalog:
    return Catalog.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
