import re
from decimal import Decimal

THOUSANDS = re.compile(r"(?<=\d)\s(?=\d{3}(?!\d))")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
MONTH = re.compile(
    r"\b(январ(?=[ьяе]\b)|феврал(?=[ьяе]\b)|март(?=[ае]?\b)|апрел(?=[ьяе]\b)|ма(?=[йяе]\b)"
    r"|июн(?=[ьяе]\b)|июл(?=[ьяе]\b)|август(?=[ае]?\b)|сентябр(?=[ьяе]\b)|октябр(?=[ьяе]\b)"
    r"|ноябр(?=[ьяе]\b)|декабр(?=[ьяе]\b))",
    re.IGNORECASE,
)


def number_key(value: str) -> str:
    return format(Decimal(value.replace(",", ".")).normalize(), "f")


def numbers(text: str) -> tuple[str, ...]:
    digits = [number_key(value) for value in NUMBER.findall(THOUSANDS.sub("", text))]
    months = [f"month:{match.group(1).lower()}" for match in MONTH.finditer(text)]
    return tuple(sorted(digits + months))


def is_duplicate(
    similarity: float, numbers_a: tuple[str, ...], numbers_b: tuple[str, ...], threshold: float
) -> bool:
    return similarity >= threshold and numbers_a == numbers_b
