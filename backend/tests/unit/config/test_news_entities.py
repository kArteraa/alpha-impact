import pytest

from shared.config.news_entities import COMPANY, COUNTRY, INDUSTRY, REGION, entity


@pytest.mark.parametrize(
    ("kind", "value", "key"),
    [
        (COUNTRY, "ОАЭ", "country:ae"),
        (COUNTRY, " Объединённые  Арабские Эмираты ", "country:ae"),
        (COUNTRY, "IN", "country:in"),
        (REGION, "Татарстан", "region:республика татарстан"),
        (REGION, "Бурятия (Республика)", "region:бурятия (республика)"),
        (INDUSTRY, "logistics", "industry:logistics"),
        (COMPANY, " Ёлки  Палки ", "company:елки палки"),
    ],
)
def test_entity_key_is_shared_by_news_and_profile_spellings(
    kind: str, value: str, key: str
) -> None:
    assert entity(kind, value) == key


@pytest.mark.parametrize(
    ("kind", "value"),
    [(COUNTRY, "Россия"), (COUNTRY, "Атлантида"), (REGION, "Алеппо"), (COMPANY, " ")],
)
def test_place_outside_vocabulary_and_blank_value_give_no_key(kind: str, value: str) -> None:
    assert entity(kind, value) is None
