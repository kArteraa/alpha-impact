from pathlib import Path

import yaml
from pydantic import BaseModel

CONFIG_FILE = Path(__file__).resolve().parent / "config.yaml"


class SizeBucket(BaseModel):
    name: str
    max_revenue_rub: float


class Confidence(BaseModel):
    linked: float
    card_only: float
    low: float


class CounterpartyConfig(BaseModel):
    payments_file: str
    top_size: int
    inflow_share_digits: int
    no_card_segment: str
    size_buckets: list[SizeBucket]
    largest_bucket: str
    confidence: Confidence


def load_config() -> CounterpartyConfig:
    return CounterpartyConfig.model_validate(
        yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8"))
    )
