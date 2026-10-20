import math
import re

from apps.services.whatif.formatting import MINUS, format_amount, format_rate
from shared.contracts.schemas import WhatIfResult

MONTHS_IN_YEAR = 12
DAYS_IN_YEAR = 365
DAYS_IN_MONTH = 30
PERCENT = 100
CURRENCY_CODE = re.compile(r"[A-Z]{3}")
RUB = "RUB"


def rate_burden(
    portfolio_amount: float, rate_now: float, rate_expected: float, months: int
) -> WhatIfResult:
    _require_positive("portfolio_amount", portfolio_amount)
    _require_positive("months", months)
    _require_non_negative("rate_now", rate_now)
    _require_non_negative("rate_expected", rate_expected)
    value = round(
        portfolio_amount * (rate_expected - rate_now) / PERCENT * months / MONTHS_IN_YEAR, 2
    )
    formula = (
        f"{format_amount(portfolio_amount)} ₽ × "
        f"({format_rate(rate_expected)}% {MINUS} {format_rate(rate_now)}%) × "
        f"{months}/{MONTHS_IN_YEAR} мес. = {format_amount(value)} ₽"
    )
    return WhatIfResult(
        kind="rate_burden",
        value=value,
        unit=RUB,
        formula=formula,
        assumptions=[
            "ставка меняется сразу и держится весь срок",
            "портфель не гасится в течение срока",
            "простые проценты без капитализации",
        ],
    )


def deposit_terms(amount: float, term_days: int, rate_path: list[float]) -> WhatIfResult:
    _require_positive("amount", amount)
    _require_positive("term_days", term_days)
    for i, rate in enumerate(rate_path):
        _require_non_negative(f"rate_path[{i}]", rate)
    months = math.ceil(term_days / DAYS_IN_MONTH)
    if len(rate_path) < months:
        raise ValueError(f"rate_path must cover {months} months, got {len(rate_path)}")
    periods = _collapse(
        [(rate_path[i], min(DAYS_IN_MONTH, term_days - i * DAYS_IN_MONTH)) for i in range(months)]
    )
    fixed = round(_interest(amount, rate_path[0], term_days), 2)
    rolling = round(sum(_interest(amount, rate, days) for rate, days in periods), 2)
    value = round(fixed - rolling, 2)
    path_terms = " + ".join(f"{format_rate(rate)}% × {days}" for rate, days in periods)
    formula = (
        f"фиксация: {format_amount(amount)} ₽ × {format_rate(rate_path[0])}% × "
        f"{term_days}/{DAYS_IN_YEAR} = {format_amount(fixed)} ₽; "
        f"переразмещение: {format_amount(amount)} ₽ × ({path_terms})/{DAYS_IN_YEAR}"
        f" = {format_amount(rolling)} ₽; разница {format_amount(value)} ₽"
    )
    return WhatIfResult(
        kind="deposit_terms",
        value=value,
        unit=RUB,
        formula=formula,
        assumptions=[
            f"год {DAYS_IN_YEAR} дней, месяц {DAYS_IN_MONTH} дней",
            "ставка фиксации равна первой точке пути ставок",
            "переразмещение каждый месяц по ставке пути",
            "без капитализации и налогов",
        ],
    )


def fx_exposure(
    amount: float, currency: str, rate_now: float, rate_forecast: float
) -> WhatIfResult:
    _require_positive("amount", amount)
    _require_positive("rate_now", rate_now)
    _require_positive("rate_forecast", rate_forecast)
    if not CURRENCY_CODE.fullmatch(currency) or currency == RUB:
        raise ValueError(f"currency must be a foreign three-letter ISO code, got {currency!r}")
    value = round(amount * (rate_forecast - rate_now), 2)
    formula = (
        f"{format_amount(amount)} {currency} × "
        f"({format_rate(rate_forecast)} {MINUS} {format_rate(rate_now)}) ₽ = "
        f"{format_amount(value)} ₽"
    )
    return WhatIfResult(
        kind="fx_exposure",
        value=value,
        unit=RUB,
        formula=formula,
        assumptions=[
            "курс к дате платежа равен прогнозному",
            "без комиссий за конвертацию",
            "без хеджирования",
        ],
    )


def _interest(amount: float, rate: float, days: int) -> float:
    return amount * rate / PERCENT * days / DAYS_IN_YEAR


def _collapse(periods: list[tuple[float, int]]) -> list[tuple[float, int]]:
    collapsed: list[tuple[float, int]] = []
    for rate, days in periods:
        if collapsed and collapsed[-1][0] == rate:
            collapsed[-1] = (rate, collapsed[-1][1] + days)
        else:
            collapsed.append((rate, days))
    return collapsed


def _require_positive(name: str, value: float) -> None:
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive finite number, got {value}")


def _require_non_negative(name: str, value: float) -> None:
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{name} must be a non-negative finite number, got {value}")
