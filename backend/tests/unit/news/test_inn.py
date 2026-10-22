import pytest

from apps.services.news.inn import inns, valid_inn

LEGAL = "7707083893"
BANK = "7728168971"
SOLE_TRADER = "500100732259"


@pytest.mark.parametrize("value", [LEGAL, BANK, SOLE_TRADER])
def test_valid_inn_passes_checksum(value: str) -> None:
    assert valid_inn(value)


@pytest.mark.parametrize(
    "value", ["7707083894", "500100732258", "500100732249", "770708389", "77070838930", "ИНН"]
)
def test_invalid_inn_is_rejected(value: str) -> None:
    assert not valid_inn(value)


def test_inns_finds_valid_numbers_in_text() -> None:
    text = f"ООО «Ромашка», ИНН {LEGAL}, КПП 773601001; ИП Иванов, ИНН {SOLE_TRADER}"

    assert inns(text) == [LEGAL, SOLE_TRADER]


def test_inns_skips_wrong_checksum_and_other_lengths() -> None:
    text = "телефон 84951234567, ОГРН 1027700132195, счёт 40702810400000012345, ИНН 7707083"

    assert inns(text) == []


def test_inns_ignores_digits_inside_longer_numbers() -> None:
    text = f"Извещение № 0373100012324{LEGAL}12 от 01.10.2026"

    assert inns(text) == []
