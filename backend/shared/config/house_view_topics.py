from collections.abc import Iterable, Mapping
from pathlib import Path
from types import MappingProxyType

import yaml

from shared.config.factors import FACTORS

TOPICS_FILE = Path(__file__).resolve().parent / "house_view_topics.yaml"


def load_topics(path: Path) -> Mapping[str, tuple[str, ...]]:
    raw: dict[str, list[str]] = yaml.safe_load(path.read_text(encoding="utf-8"))
    overlap = sorted(set(raw) & set(FACTORS))
    if overlap:
        raise ValueError(f"house view topics must not repeat factors: {overlap}")
    empty = sorted(topic for topic, factors in raw.items() if not factors)
    if empty:
        raise ValueError(f"house view topics need at least one factor: {empty}")
    unknown = sorted({factor for factors in raw.values() for factor in factors} - set(FACTORS))
    if unknown:
        raise ValueError(f"house view topics must point to known factors, unknown: {unknown}")
    return MappingProxyType({topic: tuple(factors) for topic, factors in raw.items()})


HOUSE_VIEW_TOPICS = load_topics(TOPICS_FILE)
HOUSE_VIEW_SUBJECTS: tuple[str, ...] = (*FACTORS, *HOUSE_VIEW_TOPICS)


def topics_for(factors: Iterable[str]) -> set[str]:
    known = set(factors) & set(FACTORS)
    related = {topic for topic, sources in HOUSE_VIEW_TOPICS.items() if known & set(sources)}
    return known | related
