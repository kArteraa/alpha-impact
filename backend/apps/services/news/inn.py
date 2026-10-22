import re

CANDIDATE = re.compile(r"(?<![0-9])(?:[0-9]{12}|[0-9]{10})(?![0-9])")
WEIGHTS = (3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8)
CHECK_POSITIONS = {10: (9,), 12: (10, 11)}


def check_digit(digits: str) -> str:
    weights = WEIGHTS[-len(digits) :]
    total = sum(int(digit) * weight for digit, weight in zip(digits, weights, strict=True))
    return str(total % 11 % 10)


def valid_inn(value: str) -> bool:
    if CANDIDATE.fullmatch(value) is None:
        return False
    return all(value[n] == check_digit(value[:n]) for n in CHECK_POSITIONS[len(value)])


def inns(text: str) -> list[str]:
    return [value for value in CANDIDATE.findall(text) if valid_inn(value)]
