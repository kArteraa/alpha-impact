from collections.abc import Mapping
from pathlib import Path

import yaml

OTHER = "other"
INDUSTRIES_FILE = Path(__file__).resolve().parent / "industries.yaml"
INDUSTRIES: dict[str, str] = yaml.safe_load(INDUSTRIES_FILE.read_text(encoding="utf-8"))
INDUSTRY_CLASSES = frozenset(INDUSTRIES.values()) | {OTHER}


def normalize_okved(code: str) -> str:
    parts = code.strip().split(".")
    if len(parts) > 1 and len(parts[1]) == 1:
        parts[1] += "0"
    return ".".join(parts)


def covers(prefix: str, code: str) -> bool:
    division, _, rest = prefix.partition(".")
    code_division, _, code_rest = code.partition(".")
    return division == code_division and code_rest.startswith(rest)


def industry_class(code: str, industries: Mapping[str, str]) -> str:
    matches = [prefix for prefix in industries if covers(prefix, code)]
    if not matches:
        return OTHER
    return industries[max(matches, key=len)]
