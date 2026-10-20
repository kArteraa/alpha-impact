MINUS = "−"
RUSSIAN_SEPARATORS = str.maketrans({",": " ", ".": ","})


def format_amount(value: float) -> str:
    rounded = round(value, 2)
    pattern = ",.0f" if rounded.is_integer() else ",.2f"
    return _signed(rounded, format(abs(rounded), pattern))


def format_rate(value: float) -> str:
    rounded = round(value, 2)
    return _signed(rounded, format(abs(rounded), ",.2f").rstrip("0").rstrip("."))


def _signed(value: float, digits: str) -> str:
    sign = MINUS if value < 0 else ""
    return sign + digits.translate(RUSSIAN_SEPARATORS)
