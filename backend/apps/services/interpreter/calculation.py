import math
import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date, timedelta
from itertools import pairwise

from apps.services.interpreter.context import Evidence, current_claims, source_key
from shared.config.periods import DAYS_IN_MONTH
from shared.contracts.errors import DomainError
from shared.contracts.ports import WhatIfService
from shared.contracts.schemas import (
    ActionContext,
    DepositContext,
    HouseViewClaim,
    LoanContext,
    SourceRef,
    WhatIfResult,
)

KEY_RATE = "key_rate"
RATE_DECIMALS = 2
RATE_VALUE = re.compile(r"(\d+(?:[,.]\d+)?)\s*%")
DEPOSIT_RATE = "ставка размещения следует ключевой ставке по позиции банка"
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
    now = parse_rate(facts[-1].value) if facts else None
    points = {
        claim.valid_until: parse_rate(claim.value)
        for claim in sorted(current, key=lambda c: c.date)
        if claim.type == "forecast" and claim.valid_until is not None and claim.valid_until > as_of
    }
    forecasts = tuple(
        (until, value) for until, value in sorted(points.items()) if value is not None
    )
    if now is None or not forecasts or len(forecasts) != len(points):
        return None
    return RatePoints(now=now, forecasts=forecasts)


def rate_path(points: RatePoints, as_of: date, months: int) -> list[float] | None:
    days = [as_of + timedelta(days=month * DAYS_IN_MONTH) for month in range(months)]
    if days and days[-1] > points.forecasts[-1][0]:
        return None
    anchors = [(as_of, points.now), *points.forecasts]
    return [_interpolate(anchors, day) for day in days]


def plan_calculation(
    action: ActionContext, claims: list[HouseViewClaim], as_of: date, loan_horizon_months: int
) -> Calculation | None:
    points = key_rate_points(claims, as_of)
    if points is None:
        return None
    if isinstance(action, DepositContext):
        return _deposit(action, points, as_of)
    if (
        isinstance(action, LoanContext)
        and action.product == "loan"
        and action.rate_type == "floating"
    ):
        return _loan(action, points, as_of, loan_horizon_months)
    return None


def calculation_evidence(result: WhatIfResult | None) -> dict[str, Evidence]:
    if result is None:
        return {}
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
            f"ожидаемая ставка — средняя ключевая за {months} мес. по позиции банка, линейной "
            "между прогнозами, округлена до сотых процента; итог близок к помесячному пути",
        ),
    )


def _interpolate(anchors: list[tuple[date, float]], day: date) -> float:
    (start, low), (end, high) = next(
        (left, right) for left, right in pairwise(anchors) if left[0] <= day <= right[0]
    )
    return round(low + (high - low) * (day - start).days / (end - start).days, RATE_DECIMALS)
