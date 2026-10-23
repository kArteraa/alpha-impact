from datetime import date

import pytest

from apps.services.interpreter.calculation import (
    RatePoints,
    calculation_evidence,
    key_rate_points,
    parse_rate,
    plan_calculation,
    rate_path,
)
from apps.services.whatif.service import Calculator
from shared.contracts.errors import DomainError
from shared.contracts.schemas import DepositContext, HouseViewClaim, LoanContext
from tests.unit.interpreter.support import key_rate_claim

AS_OF = date(2026, 10, 23)


SEED_RATES = [
    key_rate_claim("fact-jul", "fact", "14,25%", date(2026, 7, 24)),
    key_rate_claim("fact-sep", "fact", "14,0%", date(2026, 9, 11)),
    key_rate_claim(
        "old-2026", "forecast", "13,5%", date(2026, 9, 7), date(2026, 12, 31), "superseded"
    ),
    key_rate_claim("end-2026", "forecast", "14,0%", date(2026, 9, 11), date(2026, 12, 31)),
    key_rate_claim("end-2027", "forecast", "12,0%", date(2026, 9, 11), date(2027, 12, 31)),
]


@pytest.mark.parametrize(
    ("value", "expected"), [("14,0%", 14.0), ("14%", 14.0), ("13,75%", 13.75), (" 12,5% ", 12.5)]
)
def test_rate_value_is_parsed_from_house_view(value: str, expected: float) -> None:
    assert parse_rate(value) == expected


@pytest.mark.parametrize("value", [None, "87 руб./$", "около 14%", "14,0"])
def test_non_rate_value_is_not_parsed(value: str | None) -> None:
    assert parse_rate(value) is None


def test_points_take_latest_fact_and_current_forecasts() -> None:
    assert key_rate_points(SEED_RATES, AS_OF) == RatePoints(
        now=14.0, forecasts=((date(2026, 12, 31), 14.0), (date(2027, 12, 31), 12.0))
    )


def test_later_forecast_wins_for_the_same_horizon() -> None:
    newer = key_rate_claim("newer", "forecast", "13,0%", date(2026, 10, 1), date(2026, 12, 31))
    points = key_rate_points([*SEED_RATES, newer], AS_OF)
    assert points is not None
    assert points.forecasts[0] == (date(2026, 12, 31), 13.0)


def test_other_subjects_and_future_claims_are_ignored() -> None:
    other = key_rate_claim("fx", "forecast", "90,0%", date(2026, 9, 1), date(2026, 12, 31))
    future = key_rate_claim("future", "fact", "10,0%", date(2026, 11, 1))
    claims = [*SEED_RATES, other.model_copy(update={"subject": "fx_rate"}), future]
    points = key_rate_points(claims, AS_OF)
    assert points is not None
    assert points.now == 14.0


@pytest.mark.parametrize(
    "claims",
    [
        [claim for claim in SEED_RATES if claim.type != "fact"],
        [claim for claim in SEED_RATES if claim.type != "forecast"],
        [*SEED_RATES, key_rate_claim("vague", "forecast", "снижение", AS_OF, date(2027, 6, 30))],
        [key_rate_claim("vague-fact", "fact", "высокая", AS_OF), *SEED_RATES[2:]],
    ],
)
def test_no_points_without_parsed_fact_and_forecast(claims: list[HouseViewClaim]) -> None:
    assert key_rate_points(claims, AS_OF) is None


def test_flat_path_until_forecast() -> None:
    points = RatePoints(now=14.0, forecasts=((date(2026, 12, 31), 14.0),))
    assert rate_path(points, AS_OF, 3) == [14.0, 14.0, 14.0]


def test_path_moves_linearly_between_forecasts() -> None:
    points = RatePoints(now=14.0, forecasts=((date(2027, 10, 23), 12.0),))
    assert rate_path(points, AS_OF, 3) == [14.0, 13.84, 13.67]


def test_path_beyond_last_forecast_is_unknown() -> None:
    points = RatePoints(now=14.0, forecasts=((date(2026, 11, 30), 13.0),))
    assert rate_path(points, AS_OF, 3) is None


async def test_deposit_compares_fixing_with_rolling_on_bank_path() -> None:
    calculation = plan_calculation(
        DepositContext(amount=10_000_000, term_days=90), SEED_RATES, AS_OF, 12
    )
    assert calculation is not None
    result = await calculation.run(Calculator())
    assert result.kind == "deposit_terms"
    assert result.formula.startswith("фиксация: 10 000 000 ₽ × 14% × 90/365")
    assert "ставка размещения следует ключевой ставке по позиции банка" in result.assumptions
    assert "без капитализации и налогов" in result.assumptions


async def test_floating_loan_uses_average_bank_rate_over_horizon() -> None:
    action = LoanContext(product="loan", amount=50_000_000, rate_type="floating")
    calculation = plan_calculation(action, SEED_RATES, AS_OF, 12)
    assert calculation is not None
    result = await calculation.run(Calculator())
    assert result.kind == "rate_burden"
    assert result.formula == "50 000 000 ₽ × (13,42% − 14%) × 12/12 мес. = −290 000 ₽"
    assert result.value == -290_000.0
    assert "спред к ключевой ставке не меняется" in result.assumptions


@pytest.mark.parametrize("rate_type", ["fixed", None])
def test_loan_without_floating_rate_gets_no_calculation(rate_type: str | None) -> None:
    action = LoanContext.model_validate({"product": "loan", "amount": 1e6, "rate_type": rate_type})
    assert plan_calculation(action, SEED_RATES, AS_OF, 12) is None


def test_deposit_longer_than_bank_forecast_gets_no_calculation() -> None:
    action = DepositContext(amount=1_000_000, term_days=900)
    assert plan_calculation(action, SEED_RATES, AS_OF, 12) is None


async def test_invalid_amount_is_a_domain_error() -> None:
    calculation = plan_calculation(DepositContext(amount=0, term_days=90), SEED_RATES, AS_OF, 12)
    assert calculation is not None
    with pytest.raises(DomainError, match="amount"):
        await calculation.run(Calculator())


async def test_calculation_is_cited_as_inferred_calc_source() -> None:
    calculation = plan_calculation(
        DepositContext(amount=1_000_000, term_days=90), SEED_RATES, AS_OF, 12
    )
    assert calculation is not None
    result = await calculation.run(Calculator())
    evidence = calculation_evidence(result)
    item = evidence["calc:deposit_terms"]
    assert item.ref.kind == "calc"
    assert item.value == result.model_dump(mode="json")
    assert item.factual is False
    assert item.bank_text is None
