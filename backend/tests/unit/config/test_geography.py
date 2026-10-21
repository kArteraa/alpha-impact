import csv
from pathlib import Path

import pytest

from shared.config.geography import (
    COUNTRIES,
    REGIONS,
    Country,
    country_code,
    name_key,
    names_index,
    region_name,
)

CLIENTS_CSV = Path(__file__).parent / "fixtures" / "client_geography.csv"


def client_rows() -> list[dict[str, str]]:
    with CLIENTS_CSV.open(encoding="utf-8") as file:
        return list(csv.DictReader(file, delimiter=";"))


def test_name_key_ignores_case_spacing_and_yo() -> None:
    assert name_key(" Объединённые  Арабские Эмираты ") == "объединенные арабские эмираты"


def test_every_client_region_is_known() -> None:
    assert all(region_name(row["REGION"]) == row["REGION"] for row in client_rows())


def test_every_client_country_is_known() -> None:
    names = [
        name.strip()
        for row in client_rows()
        for name in row["FTS_COUNTRY_NAME"].split(",")
        if name.strip()
    ]

    assert names
    assert all(country_code(name) in COUNTRIES for name in names)


@pytest.mark.parametrize(
    ("name", "code"),
    [
        ("ОАЭ", "ae"),
        ("Объединенные Арабские Эмираты", "ae"),
        ("United Arab Emirates", "ae"),
        ("КИТАЙ", "cn"),
        ("cn", "cn"),
        ("ЮЖНАЯ КОРЕЯ", "kr"),
        ("БЕЛАРУСЬ", "by"),
        ("КОНГО", "cg"),
        ("КОТ Д'ИВУАР", "ci"),
        ("США", "us"),
        ("АБХАЗИЯ", "ab"),
        ("ЮЖНАЯ ОСЕТИЯ", "os"),
    ],
)
def test_country_is_found_by_code_and_any_name(name: str, code: str) -> None:
    assert country_code(name) == code


def test_russia_is_neither_region_nor_country() -> None:
    assert [region_name(name) for name in ("Россия", "Russia")] == [None, None]
    assert [country_code(name) for name in ("Россия", "Russia", "ru")] == [None, None, None]


def test_region_is_returned_as_written_in_csv() -> None:
    assert region_name("республика татарстан") == "Республика Татарстан"
    assert region_name("БУРЯТИЯ (РЕСПУБЛИКА)") == "Бурятия (Республика)"
    assert region_name("Татарстан") is None
    assert len({name_key(name) for name in REGIONS}) == len(REGIONS)


def test_name_shared_by_two_countries_is_rejected() -> None:
    countries = {
        "cg": Country(ru="Конго", en="Congo", aliases=()),
        "cd": Country(ru="ДР Конго", en="DR Congo", aliases=("конго",)),
    }

    with pytest.raises(ValueError, match="конго"):
        names_index(countries)
