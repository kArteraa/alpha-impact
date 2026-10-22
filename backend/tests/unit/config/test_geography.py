import csv
from pathlib import Path

import pytest

from shared.config.geography import (
    COUNTRIES,
    REGION_LABELS,
    REGIONS,
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


@pytest.mark.parametrize(
    ("name", "region"),
    [
        ("республика татарстан", "Республика Татарстан"),
        ("Татарстан", "Республика Татарстан"),
        ("БУРЯТИЯ (РЕСПУБЛИКА)", "Бурятия (Республика)"),
        ("Бурятия", "Бурятия (Республика)"),
        ("Якутия", "Саха (Республика) (Якутия)"),
        ("Адыгея", "Адыгея (Республика) (Адыгея)"),
        ("Чувашия", "Чувашская Республика-Чувашия"),
        ("Республика Саха (Якутия)", "Саха (Республика) (Якутия)"),
        ("Республика Адыгея", "Адыгея (Республика) (Адыгея)"),
        ("Севастополь", "Севастополь"),
    ],
)
def test_region_is_returned_as_written_in_csv(name: str, region: str) -> None:
    assert region_name(name) == region


def test_model_sees_common_and_official_names_of_every_subject() -> None:
    labels = {"Якутия", "Республика Саха (Якутия)", "Татарстан", "Москва", "Херсонская область"}

    assert len(REGIONS) == 90
    assert labels <= set(REGION_LABELS)
    assert "Саха (Республика) (Якутия)" not in REGION_LABELS


def test_name_shared_by_two_places_is_rejected() -> None:
    with pytest.raises(ValueError, match="конго"):
        names_index({"cg": ("cg", "Конго"), "cd": ("cd", "ДР Конго", "конго")})
