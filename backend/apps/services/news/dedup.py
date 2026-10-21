import re

THOUSANDS = re.compile(r"(?<=\d)\s(?=\d{3}(?!\d))")
NUMBER = re.compile(r"\d+(?:[.,]\d+)?")
MONTH = re.compile(
    r"\b(январ|феврал|март|апрел|ма(?=[йяе]\b)|июн|июл|август|сентябр|октябр|ноябр|декабр)[а-я]*",
    re.IGNORECASE,
)


def numbers(text: str) -> tuple[str, ...]:
    digits = [value.replace(",", ".") for value in NUMBER.findall(THOUSANDS.sub("", text))]
    months = [f"month:{match.group(1).lower()}" for match in MONTH.finditer(text)]
    return tuple(sorted(digits + months))


def is_duplicate(
    similarity: float, numbers_a: tuple[str, ...], numbers_b: tuple[str, ...], threshold: float
) -> bool:
    return similarity >= threshold and numbers_a == numbers_b
