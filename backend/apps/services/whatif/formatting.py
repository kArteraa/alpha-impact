from decimal import Decimal

MINUS = "−"
RUSSIAN_SEPARATORS = str.maketrans({",": " ", ".": ","})


def format_amount(value: float) -> str:
    rounded = round(value, 2)
    pattern = ",.0f" if rounded.is_integer() else ",.2f"
    return _signed(rounded, format(abs(rounded), pattern))


def format_rate(value: float) -> str:
    whole, _, fraction = format(Decimal(repr(abs(value))).normalize(), "f").partition(".")
    digits = f"{int(whole):,}" + (f".{fraction}" if fraction else "")
    return _signed(value, digits)


def _signed(value: float, digits: str) -> str:
    sign = MINUS if value < 0 else ""
    return sign + digits.translate(RUSSIAN_SEPARATORS)
