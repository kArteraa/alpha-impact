from datetime import date
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

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
    llm_task: str
    extra_subjects: list[str]
    system_prompt: str
    documents: list[Document]

    @property
    def subjects(self) -> list[str]:
        return [*FACTORS, *self.extra_subjects]


def read_yaml(name: str) -> Any:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def load_config() -> IngestConfig:
    return IngestConfig.model_validate(
        {**read_yaml("config.yaml"), "documents": read_yaml("documents.yaml")}
    )
