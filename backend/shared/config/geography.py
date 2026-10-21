from collections.abc import Mapping
from pathlib import Path
from types import MappingProxyType

import yaml
from pydantic import BaseModel, ConfigDict, TypeAdapter

CONFIG_DIR = Path(__file__).resolve().parent
REGIONS_FILE = CONFIG_DIR / "regions.yaml"
COUNTRIES_FILE = CONFIG_DIR / "countries.yaml"


class Country(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    ru: str
    en: str
    aliases: tuple[str, ...]


def name_key(value: str) -> str:
    return " ".join(value.split()).casefold().replace("ё", "е")


def names_index(countries: Mapping[str, Country]) -> Mapping[str, str]:
    index: dict[str, str] = {}
    for code, country in countries.items():
        for name in (code, country.ru, country.en, *country.aliases):
            known = index.setdefault(name_key(name), code)
            if known != code:
                raise ValueError(f"{name_key(name)!r} names both {known!r} and {code!r}")
    return MappingProxyType(index)


def load_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


REGIONS = TypeAdapter(tuple[str, ...]).validate_python(load_yaml(REGIONS_FILE))
REGION_NAMES: Mapping[str, str] = MappingProxyType({name_key(name): name for name in REGIONS})
COUNTRIES: Mapping[str, Country] = MappingProxyType(
    TypeAdapter(dict[str, Country]).validate_python(load_yaml(COUNTRIES_FILE))
)
COUNTRY_CODES = names_index(COUNTRIES)


def region_name(name: str) -> str | None:
    return REGION_NAMES.get(name_key(name))


def country_code(name: str) -> str | None:
    return COUNTRY_CODES.get(name_key(name))
