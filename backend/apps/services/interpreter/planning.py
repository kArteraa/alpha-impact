from pathlib import Path
from typing import Literal, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator

from shared.config.factors import FACTORS
from shared.contracts.errors import DomainError
from shared.contracts.schemas import HouseViewClaim

PLANS_PATH = Path(__file__).with_name("plans.yaml")
BUSINESS_ACTIONS = {"payment", "deposit", "fx", "loan", "payroll", "dashboard"}


class Template(BaseModel):
    model_config = ConfigDict(extra="forbid")
    focus: str = Field(min_length=1)
    context: list[Literal["profile", "counterparty", "news", "house_view"]]


class PlanConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lookback_days: int = Field(gt=0)
    search_limit: int = Field(gt=0)
    max_tool_calls: int = Field(gt=0)
    trace_summary_chars: int = Field(gt=0)
    templates: dict[str, Template]

    @model_validator(mode="after")
    def complete_templates(self) -> Self:
        if set(self.templates) != BUSINESS_ACTIONS:
            raise ValueError("Templates must cover all business actions")
        for action, template in self.templates.items():
            required = {"profile", "news", "house_view"}
            if action == "payment":
                required.add("counterparty")
            if set(template.context) != required or len(template.context) != len(required):
                raise ValueError(f"Invalid context for {action}")
        return self


class ToolCall(BaseModel):
    model_config = ConfigDict(extra="forbid")
    tool: Literal["house_view.claims", "house_view.chain"]
    argument: str = Field(min_length=1)


class Plan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    focus: str = Field(min_length=1)
    tools: list[ToolCall]

    def validate_tools(self, config: PlanConfig, claims: list[HouseViewClaim]) -> None:
        if len(self.tools) > config.max_tool_calls:
            raise DomainError("Plan exceeds the configured tool limit")
        known_claims = {claim.id for claim in claims}
        seen: set[tuple[str, str]] = set()
        for call in self.tools:
            allowed = FACTORS if call.tool == "house_view.claims" else known_claims
            if call.argument not in allowed or (call.tool, call.argument) in seen:
                raise DomainError("Plan contains an unknown or duplicate tool argument")
            seen.add((call.tool, call.argument))


def load_config(path: Path) -> PlanConfig:
    return PlanConfig.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
