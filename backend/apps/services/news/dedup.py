import re

THOUSANDS = re.compile(r"(?<=\d)[\s  ](?=\d{3}(?!\d))")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
MONTH_STEMS = (
    "январ",
    "феврал",
    "март",
    "апрел",
    "ма",
    "июн",
    "июл",
    "август",
    "сентябр",
    "октябр",
    "ноябр",
    "декабр",
)
MONTH = re.compile(
    r"\b(январ|феврал|март|апрел|июн|июл|август|сентябр|октябр|ноябр|декабр)[а-я]*|\b(ма)[йяе]\b",
    re.IGNORECASE,
)


def months(text: str) -> list[str]:
    stems = ((match.group(1) or match.group(2)).lower() for match in MONTH.finditer(text))
    return [f"month:{MONTH_STEMS.index(stem) + 1}" for stem in stems]


def numbers(text: str) -> tuple[str, ...]:
    digits = [value.replace(",", ".") for value in NUMBER.findall(THOUSANDS.sub("", text))]
    return tuple(sorted(digits + months(text)))


def is_duplicate(
    similarity: float, numbers_a: tuple[str, ...], numbers_b: tuple[str, ...], threshold: float
) -> bool:
    return similarity >= threshold and numbers_a == numbers_b
