from pathlib import Path

import yaml
from pydantic import BaseModel, model_validator

from shared.config.factors import FACTORS
from shared.config.industries import INDUSTRY_CLASSES, OTHER
from shared.config.news_entities import PRODUCTS

CONFIG_FILE = Path(__file__).resolve().parent / "config.yaml"


class NewsConfig(BaseModel):
    llm_task: str
    max_text_chars: int
    max_factors: int
    max_entities: int
    max_age_days: int
    dedup_threshold: float
    dedup_window_hours: int
    dedup_candidates: int
    fetch_timeout_seconds: float
    max_feed_bytes: int
    user_agent: str
    factor_hints: dict[str, str]
    industry_hints: dict[str, str]
    product_hints: dict[str, str]
    system_prompt: str

    @model_validator(mode="after")
    def hints_cover_vocabularies(self) -> "NewsConfig":
        if set(self.factor_hints) != set(FACTORS):
            raise ValueError(f"factor_hints must describe exactly the factors: {FACTORS}")
        industries = INDUSTRY_CLASSES - {OTHER}
        if set(self.industry_hints) != industries:
            raise ValueError(
                f"industry_hints must describe exactly the industries: {sorted(industries)}"
            )
        if set(self.product_hints) != set(PRODUCTS):
            raise ValueError(f"product_hints must describe exactly the products: {PRODUCTS}")
        return self

    @property
    def prompt(self) -> str:
        factors = "\n".join(f"- {name}: {self.factor_hints[name]}" for name in FACTORS)
        industries = "\n".join(f"- {name}: {hint}" for name, hint in self.industry_hints.items())
        products = "\n".join(f"- {name}: {self.product_hints[name]}" for name in PRODUCTS)
        return (
            f"{self.system_prompt}\nФакторы:\n{factors}"
            f"\nОтрасли:\n{industries}\nПродукты:\n{products}"
        )


def load_config() -> NewsConfig:
    return NewsConfig.model_validate(yaml.safe_load(CONFIG_FILE.read_text(encoding="utf-8")))
