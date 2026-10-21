import hashlib
from collections.abc import Sequence

from pydantic import BaseModel, Field, field_validator

from apps.services.news.config import NewsConfig
from apps.services.news.feed import FeedEntry
from shared.config.factors import FACTORS
from shared.config.news_entities import (
    COMPANY,
    COUNTRY,
    INDUSTRY,
    PRODUCT,
    PRODUCTS,
    REGION,
    entity,
    normalized,
)
from shared.contracts.ports import LLMGateway
from shared.contracts.schemas import Factor, NewsItem

ID_LENGTH = 32


class Annotation(BaseModel):
    factors: Sequence[Factor]
    industries: Sequence[str]
    regions: Sequence[str]
    countries: Sequence[str]
    companies: Sequence[str]
    products: Sequence[str]


def annotation_schema(config: NewsConfig) -> type[Annotation]:
    known_factors = frozenset(FACTORS)
    known_industries = frozenset(config.industry_hints)

    class KnownFactor(Factor):
        name: str = Field(json_schema_extra={"enum": list(FACTORS)})

        @field_validator("name")
        @classmethod
        def known_name(cls, value: str) -> str:
            if value not in known_factors:
                raise ValueError(f"unknown factor {value!r}")
            return value

    class NewsAnnotation(Annotation):
        factors: list[KnownFactor] = Field(max_length=config.max_factors)
        industries: list[str] = Field(
            max_length=config.max_entities,
            json_schema_extra={"items": {"type": "string", "enum": list(config.industry_hints)}},
        )
        regions: list[str] = Field(max_length=config.max_entities)
        countries: list[str] = Field(max_length=config.max_entities)
        companies: list[str] = Field(max_length=config.max_entities)
        products: list[str] = Field(
            max_length=config.max_entities,
            json_schema_extra={"items": {"type": "string", "enum": list(PRODUCTS)}},
        )

        @field_validator("products")
        @classmethod
        def known_products(cls, values: list[str]) -> list[str]:
            unknown = [value for value in values if value not in PRODUCTS]
            if unknown:
                raise ValueError(f"unknown products {unknown!r}")
            return values

        @field_validator("industries")
        @classmethod
        def known_industries(cls, values: list[str]) -> list[str]:
            unknown = [value for value in values if value not in known_industries]
            if unknown:
                raise ValueError(f"unknown industries {unknown!r}")
            return values

    return NewsAnnotation


def news_id(title: str) -> str:
    return hashlib.sha256(normalized(title).encode()).hexdigest()[:ID_LENGTH]


def entities(annotation: Annotation) -> list[str]:
    groups = (
        (INDUSTRY, annotation.industries),
        (REGION, annotation.regions),
        (COUNTRY, annotation.countries),
        (COMPANY, annotation.companies),
        (PRODUCT, annotation.products),
    )
    keys = [entity(kind, value) for kind, values in groups for value in values if value.strip()]
    return list(dict.fromkeys(keys))


def entry_prompt(title: str, text: str, max_chars: int) -> str:
    return f"Заголовок: {title}\nТекст: {text[:max_chars]}"


async def annotate(
    llm: LLMGateway, config: NewsConfig, schema: type[Annotation], title: str, text: str
) -> tuple[Annotation, int, int]:
    prompt = entry_prompt(title, text, config.max_text_chars)
    answer, tokens_in, tokens_out = await llm.complete(
        config.llm_task, config.prompt, prompt, schema
    )
    if not isinstance(answer, Annotation):
        raise TypeError(f"LLM gateway returned {type(answer).__name__}, not {schema.__name__}")
    return answer, tokens_in, tokens_out


def to_news_item(entry: FeedEntry, annotation: Annotation) -> NewsItem:
    return NewsItem(
        id=news_id(entry.title),
        title=entry.title,
        text=entry.text,
        url=entry.url,
        published_at=entry.published_at,
        source=entry.source,
        entities=entities(annotation),
        factors=[Factor.model_validate(factor.model_dump()) for factor in annotation.factors],
    )
