from typing import Any

import pytest
from pydantic import ValidationError

from apps.services.news.annotation import annotation_schema, news_id, to_news_item
from apps.services.news.config import load_config
from apps.services.news.feed import FeedEntry
from shared.config.factors import FACTORS
from shared.config.geography import COUNTRIES, REGIONS
from tests.news_data import KEY_RATE_ANSWER, NOW

CONFIG = load_config()
SCHEMA = annotation_schema(CONFIG)


def answer(**changes: Any) -> dict[str, Any]:
    return {**KEY_RATE_ANSWER, **changes}


def test_schema_accepts_vocabulary_answer() -> None:
    assert SCHEMA.model_validate(KEY_RATE_ANSWER)


def test_schema_rejects_factor_outside_vocabulary() -> None:
    factor = {"name": "inflation", "direction": "up", "strength": 0.5, "horizon": "month"}
    with pytest.raises(ValidationError, match="inflation"):
        SCHEMA.model_validate(answer(factors=[factor]))


def test_schema_rejects_industry_outside_vocabulary() -> None:
    with pytest.raises(ValidationError, match="space"):
        SCHEMA.model_validate(answer(industries=["space"]))


def test_schema_limits_list_lengths() -> None:
    factor = KEY_RATE_ANSWER["factors"][0]
    with pytest.raises(ValidationError):
        SCHEMA.model_validate(answer(factors=[factor] * (CONFIG.max_factors + 1)))
    with pytest.raises(ValidationError):
        SCHEMA.model_validate(answer(companies=["x"] * (CONFIG.max_entities + 1)))


def test_schema_shows_vocabularies_to_the_model() -> None:
    schema = str(SCHEMA.model_json_schema())

    assert all(name in schema for name in FACTORS)
    assert all(name in schema for name in CONFIG.industry_hints)
    assert all(label in schema for label in REGIONS.values())
    assert all(f"'{code}'" in schema for code in COUNTRIES)


@pytest.mark.parametrize("field", ["regions", "countries"])
def test_schema_rejects_russia(field: str) -> None:
    with pytest.raises(ValidationError, match="Россия"):
        SCHEMA.model_validate(answer(**{field: ["Россия"]}))


def test_schema_rejects_region_outside_vocabulary() -> None:
    with pytest.raises(ValidationError, match="Алеппо"):
        SCHEMA.model_validate(answer(regions=["Алеппо"]))


def test_schema_spells_regions_as_csv_and_countries_as_codes() -> None:
    annotation = SCHEMA.model_validate(
        answer(regions=["Татарстан", "якутия"], countries=["ОАЭ", "Китай", "tr"])
    )

    assert annotation.regions == ["Республика Татарстан", "Саха (Республика) (Якутия)"]
    assert annotation.countries == ["ae", "cn", "tr"]


def test_answer_becomes_news_item_with_prefixed_entities() -> None:
    annotation = SCHEMA.model_validate(
        answer(regions=["Москва", " москва "], companies=["Сбербанк", "СБЕРБАНК"])
    )

    entry = FeedEntry("Ставка", "Текст", "https://a.example/1", NOW, "a.example")

    news = to_news_item(entry, annotation)

    assert news.entities == [
        "industry:finance",
        "region:москва",
        "country:cn",
        "company:сбербанк",
    ]
    assert [factor.name for factor in news.factors] == ["key_rate"]
    assert (news.id, news.source, news.published_at) == (news_id("Ставка"), "a.example", NOW)


def test_news_id_ignores_case_and_spacing_of_title() -> None:
    assert news_id("ЦБ  снизил ставку ") == news_id("цб снизил ставку")
    assert news_id("ЦБ снизил ставку") != news_id("ЦБ повысил ставку")
