from datetime import date
from pathlib import Path

import yaml
from pydantic import BaseModel

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
    subjects: list[str]
    system_prompt: str
    documents: list[Document]


def read_yaml(name: str) -> object:
    return yaml.safe_load((CONFIG_DIR / name).read_text(encoding="utf-8"))


def load_config() -> IngestConfig:
    settings = read_yaml("config.yaml")
    assert isinstance(settings, dict)
    return IngestConfig.model_validate({**settings, "documents": read_yaml("documents.yaml")})
