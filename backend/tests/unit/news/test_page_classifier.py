from typing import Any

import pytest
from pydantic import ValidationError

from apps.services.news.annotation import page_schema
from apps.services.news.config import load_config
from apps.services.news.service import PageClassifier
from shared.contracts.schemas import PageContext
from tests.news_data import EMPTY_ANSWER, KEY_RATE_ANSWER, FakeNewsLlm

CONFIG = load_config()
CUSTOMER = "7707083893"
SUPPLIER = "7728168971"
ARTICLE = PageContext(
    url="https://www.rbc.ru/economics/22/10/2026/rate",
    text="Ставка снижена. Банк России снизил ключевую ставку до 16% годовых.",
)
COUNTERPARTY = PageContext(
    url="https://www.rusprofile.ru/id/123",
    text=f"АО «Перевозчик», ИНН {SUPPLIER}, ИНН учредителя 7707083894, грузовые перевозки",
)
TENDER = PageContext(
    url="https://zakupki.gov.ru/epz/order/notice/ea20/view/common-info.html?regNumber=1",
    text=(
        f"Извещение № 03731000123240001230000 по 44-ФЗ. Заказчик: ПАО, ИНН {CUSTOMER}. "
        "Поставка дизельного топлива, начальная цена 12 500 000 руб."
    ),
)


def answer(page_type: str, **changes: Any) -> dict[str, Any]:
    return {**EMPTY_ANSWER, "page_type": page_type, **changes}


async def test_article_page_is_marked_up_like_news() -> None:
    llm = FakeNewsLlm(answers={"Ставка снижена": {**KEY_RATE_ANSWER, "page_type": "article"}})

    page_type, entities, factors = await PageClassifier(llm, CONFIG).classify(ARTICLE)

    assert page_type == "article"
    assert [factor.name for factor in factors] == ["key_rate"]
    assert {"industry:finance", "region:москва", "country:cn", "company:сбербанк"} <= set(entities)
    assert llm.tasks == [CONFIG.llm_task]


async def test_counterparty_page_keeps_only_inn_with_valid_checksum() -> None:
    llm = FakeNewsLlm(answers={"Перевозчик": answer("counterparty", industries=["logistics"])})

    page_type, entities, factors = await PageClassifier(llm, CONFIG).classify(COUNTERPARTY)

    assert page_type == "counterparty"
    assert entities == ["industry:logistics", f"inn:{SUPPLIER}"]
    assert factors == []


async def test_tender_page_finds_customer_inn_but_not_notice_number() -> None:
    llm = FakeNewsLlm(answers={"Извещение": answer("tender", industries=["fuel"])})

    page_type, entities, _ = await PageClassifier(llm, CONFIG).classify(TENDER)

    assert page_type == "tender"
    assert entities == ["industry:fuel", f"inn:{CUSTOMER}"]


async def test_extension_entities_give_only_valid_inns() -> None:
    page = ARTICLE.model_copy(
        update={"entities": [f"inn:{SUPPLIER}", "inn:7707083894", "industry:finance", "inn:x"]}
    )
    llm = FakeNewsLlm(answers={"Ставка снижена": answer("article")})

    _, entities, _ = await PageClassifier(llm, CONFIG).classify(page)

    assert entities == [f"inn:{SUPPLIER}"]


async def test_inn_found_twice_gives_one_entity() -> None:
    page = COUNTERPARTY.model_copy(update={"entities": [f"inn:{SUPPLIER}"]})
    llm = FakeNewsLlm(answers={"Перевозчик": answer("counterparty")})

    _, entities, _ = await PageClassifier(llm, CONFIG).classify(page)

    assert entities == [f"inn:{SUPPLIER}"]


async def test_prompt_carries_url_and_text_cut_to_limit() -> None:
    page = PageContext(url="https://a.example/page", text="я" * (CONFIG.max_text_chars * 2))
    llm = FakeNewsLlm(answers={"a.example": answer("article")})

    await PageClassifier(llm, CONFIG).classify(page)

    assert "https://a.example/page" in llm.completions[0]
    assert llm.completions[0].count("я") == CONFIG.max_text_chars


async def test_unknown_page_type_from_model_is_rejected() -> None:
    llm = FakeNewsLlm(answers={"Ставка снижена": answer("blog")})

    with pytest.raises(ValidationError, match="page_type"):
        await PageClassifier(llm, CONFIG).classify(ARTICLE)


def test_model_sees_page_types() -> None:
    schema = page_schema(CONFIG).model_json_schema()

    assert schema["properties"]["page_type"]["enum"] == list(CONFIG.page_types)
