from shared.contracts.schemas import CounterpartyContext


class CounterpartyAggregates:
    async def context(
        self, client_id: str, beneficiary_id: str | None, inn: str | None
    ) -> CounterpartyContext:
        raise NotImplementedError("AH-8")
