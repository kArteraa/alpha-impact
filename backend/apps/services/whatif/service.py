from apps.services.whatif import formulas
from shared.contracts.schemas import WhatIfResult


class Calculator:
    async def rate_burden(
        self, portfolio_amount: float, rate_now: float, rate_expected: float, months: int
    ) -> WhatIfResult:
        return formulas.rate_burden(portfolio_amount, rate_now, rate_expected, months)

    async def deposit_terms(
        self, amount: float, term_days: int, rate_path: list[float]
    ) -> WhatIfResult:
        return formulas.deposit_terms(amount, term_days, rate_path)

    async def fx_exposure(
        self, amount: float, currency: str, rate_now: float, rate_forecast: float
    ) -> WhatIfResult:
        return formulas.fx_exposure(amount, currency, rate_now, rate_forecast)
