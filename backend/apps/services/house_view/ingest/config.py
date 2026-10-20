from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, model_validator

from shared.config.factors import FACTORS

CONFIG_DIR = Path(__file__).resolve().parent


class Document(BaseModel):
    file: str
    title: str
    date: date
    expired: bool = False


class IngestConfig(BaseModel):
    ocr_languages: str
    max_page_chars: int
    min_page_chars: int
    llm_task: str
    max_claims_per_page: int
    subject_hints: dict[str, str]
    extra_subjects: list[str]
    system_prompt: str
    documents: list[Document]

    @model_validator(mode="after")
    def hints_cover_subjects(self) -> "IngestConfig":
        if set(self.subject_hints) != set(self.subjects):
            raise ValueError(f"subject_hints must describe exactly the subjects: {self.subjects}")
        return self

    @property
    def subjects(self) -> list[str]:
        return [*FACTORS, *self.extra_subjects]

    @property
    def prompt(self) -> str:
        hints = "\n".join(f"- {name}: {self.subject_hints[name]}" for name in self.subjects)
        return f"{self.system_prompt}\nТемы:\n{hints}"


def read_yaml(name: str) -> Any:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def load_config() -> IngestConfig:
    return IngestConfig.model_validate(
        {**read_yaml("config.yaml"), "documents": read_yaml("documents.yaml")}
    )
