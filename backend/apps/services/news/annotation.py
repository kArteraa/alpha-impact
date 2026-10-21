import hashlib
from collections.abc import Callable, Sequence

from pydantic import BaseModel, Field, JsonValue, field_validator
from pydantic.json_schema import JsonDict

from apps.services.news.config import NewsConfig
from apps.services.news.feed import FeedEntry
from shared.config.factors import FACTORS
from shared.config.geography import (
    COUNTRIES,
    REGION_LABELS,
    country_code,
    name_key,
    region_name,
)
from shared.contracts.ports import LLMGateway
from shared.contracts.schemas import Factor, NewsItem

ID_LENGTH = 32
INDUSTRY = "industry"
REGION = "region"
COUNTRY = "country"
COMPANY = "company"


def resolved(values: list[str], resolve: Callable[[str], str | None], kind: str) -> list[str]:
    names = {value: resolve(value) for value in values}
    unknown = [value for value, name in names.items() if name is None]
    if unknown:
        raise ValueError(f"unknown {kind} {unknown!r}")
    return [name for name in names.values() if name is not None]


def vocabulary(names: Sequence[str]) -> JsonDict:
    enum: list[JsonValue] = list(names)
    return {"items": {"type": "string", "enum": enum}}


class Annotation(BaseModel):
    factors: Sequence[Factor]
    industries: Sequence[str]
    regions: Sequence[str]
    countries: Sequence[str]
    companies: Sequence[str]


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
            json_schema_extra=vocabulary(list(config.industry_hints)),
        )
        regions: list[str] = Field(
            max_length=config.max_entities, json_schema_extra=vocabulary(REGION_LABELS)
        )
        countries: list[str] = Field(
            max_length=config.max_entities, json_schema_extra=vocabulary(list(COUNTRIES))
        )
        companies: list[str] = Field(max_length=config.max_entities)

        @field_validator("industries")
        @classmethod
        def known_industries(cls, values: list[str]) -> list[str]:
            unknown = [value for value in values if value not in known_industries]
            if unknown:
                raise ValueError(f"unknown industries {unknown!r}")
            return values

        @field_validator("regions")
        @classmethod
        def known_regions(cls, values: list[str]) -> list[str]:
            return resolved(values, region_name, "regions")

        @field_validator("countries")
        @classmethod
        def known_countries(cls, values: list[str]) -> list[str]:
            return resolved(values, country_code, "countries")

    return NewsAnnotation


def normalized(value: str) -> str:
    return " ".join(value.split()).casefold()


def news_id(title: str) -> str:
    return hashlib.sha256(normalized(title).encode()).hexdigest()[:ID_LENGTH]


def entity(kind: str, value: str) -> str:
    return f"{kind}:{name_key(value)}"


def entities(annotation: Annotation) -> list[str]:
    groups = (
        (INDUSTRY, annotation.industries),
        (REGION, annotation.regions),
        (COUNTRY, annotation.countries),
        (COMPANY, annotation.companies),
    )
    keys = [entity(kind, value) for kind, values in groups for value in values if value.strip()]
    return list(dict.fromkeys(keys))


def news_factors(annotation: Annotation) -> list[Factor]:
    return [Factor.model_validate(factor.model_dump()) for factor in annotation.factors]


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
        factors=news_factors(annotation),
    )
