from shared.contracts.schemas import WhatIfResult


class Calculator:
    async def rate_burden(
        self, portfolio_amount: float, rate_now: float, rate_expected: float, months: int
    ) -> WhatIfResult:
        raise NotImplementedError("AH-24")

    async def deposit_terms(
        self, amount: float, term_days: int, rate_path: list[float]
    ) -> WhatIfResult:
        raise NotImplementedError("AH-24")

    async def fx_exposure(
        self, amount: float, currency: str, rate_now: float, rate_forecast: float
    ) -> WhatIfResult:
        raise NotImplementedError("AH-24")
