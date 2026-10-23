import math
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, timedelta

from apps.services.interpreter.context import Evidence, current_claims, source_key
from shared.contracts.errors import DomainError
from shared.contracts.ports import WhatIfService
from shared.contracts.schemas import (
    DepositContext,
    HouseViewClaim,
    LoanContext,
    SourceRef,
    WhatIfResult,
)

KEY_RATE = "key_rate"
DAYS_IN_MONTH = 30
RATE_DECIMALS = 2
RATE_VALUE = re.compile(r"(\d+(?:,\d+)?)%")
DEPOSIT_RATE = "ставка депозита следует ключевой ставке по позиции банка"
LINEAR_PATH = "между прогнозами банка ключевая ставка меняется линейно"
FIXED_SPREAD = "спред к ключевой ставке не меняется"
TITLES = {
    "deposit_terms": "Расчёт: фиксация ставки против помесячного переразмещения",
    "rate_burden": "Расчёт: процентные расходы при плавающей ставке",
}


@dataclass(frozen=True)
class RatePoints:
    now: float
    forecasts: tuple[tuple[date, float], ...]


@dataclass(frozen=True)
class Calculation:
    name: str
    summary: str
    call: Callable[[WhatIfService], Awaitable[WhatIfResult]]
    assumptions: tuple[str, ...]

    async def run(self, whatif: WhatIfService) -> WhatIfResult:
        try:
            result = await self.call(whatif)
        except ValueError as error:
            raise DomainError(str(error)) from error
        return result.model_copy(update={"assumptions": [*result.assumptions, *self.assumptions]})


def parse_rate(value: str | None) -> float | None:
    if value is None:
        return None
    match = RATE_VALUE.fullmatch(value.strip())
    return float(match.group(1).replace(",", ".")) if match else None


def key_rate_points(claims: list[HouseViewClaim], as_of: date) -> RatePoints | None:
    current = [claim for claim in current_claims(claims, as_of) if claim.subject == KEY_RATE]
    facts = sorted((claim for claim in current if claim.type == "fact"), key=lambda c: c.date)
    forecasts = sorted(
        (
            claim
            for claim in current
            if claim.type == "forecast"
            and claim.valid_until is not None
            and claim.valid_until > as_of
        ),
        key=lambda claim: claim.date,
    )
    if not facts or not forecasts:
        return None
    now = parse_rate(facts[-1].value)
    points: dict[date, float] = {}
    for claim in forecasts:
        value = parse_rate(claim.value)
        if value is None or claim.valid_until is None:
            return None
        points[claim.valid_until] = value
    if now is None:
        return None
    return RatePoints(now=now, forecasts=tuple(sorted(points.items())))


def rate_path(points: RatePoints, as_of: date, months: int) -> list[float] | None:
    anchors = [(as_of, points.now), *points.forecasts]
    path = []
    for month in range(months):
        rate = _interpolate(anchors, as_of + timedelta(days=month * DAYS_IN_MONTH))
        if rate is None:
            return None
        path.append(rate)
    return path


def plan_calculation(
    action: DepositContext | LoanContext,
    claims: list[HouseViewClaim],
    as_of: date,
    loan_horizon_months: int,
) -> Calculation | None:
    if isinstance(action, LoanContext) and action.rate_type != "floating":
        return None
    points = key_rate_points(claims, as_of)
    if points is None:
        return None
    if isinstance(action, DepositContext):
        return _deposit(action, points, as_of)
    return _loan(action, points, as_of, loan_horizon_months)


def calculation_evidence(result: WhatIfResult) -> dict[str, Evidence]:
    ref = SourceRef(kind="calc", id=result.kind, title=TITLES[result.kind])
    return {source_key(ref): Evidence(ref, result.model_dump(mode="json"), None, False)}


def _deposit(action: DepositContext, points: RatePoints, as_of: date) -> Calculation | None:
    path = rate_path(points, as_of, math.ceil(action.term_days / DAYS_IN_MONTH))
    if path is None:
        return None
    return Calculation(
        name="deposit_terms",
        summary=f"amount={action.amount}, term_days={action.term_days}, rate_path={path}",
        call=lambda whatif: whatif.deposit_terms(action.amount, action.term_days, path),
        assumptions=(DEPOSIT_RATE, LINEAR_PATH),
    )


def _loan(action: LoanContext, points: RatePoints, as_of: date, months: int) -> Calculation | None:
    path = rate_path(points, as_of, months)
    if path is None:
        return None
    expected = round(sum(path) / len(path), RATE_DECIMALS)
    return Calculation(
        name="rate_burden",
        summary=f"amount={action.amount}, rate_now={points.now}, rate_expected={expected}, "
        f"months={months}",
        call=lambda whatif: whatif.rate_burden(action.amount, points.now, expected, months),
        assumptions=(
            FIXED_SPREAD,
            f"ожидаемая ставка — средняя ключевая по позиции банка за {months} мес.",
            LINEAR_PATH,
        ),
    )


def _interpolate(anchors: list[tuple[date, float]], day: date) -> float | None:
    for (start, low), (end, high) in zip(anchors, anchors[1:], strict=False):
        if start <= day <= end:
            rate = low + (high - low) * (day - start).days / (end - start).days
            return round(rate, RATE_DECIMALS)
    return None
