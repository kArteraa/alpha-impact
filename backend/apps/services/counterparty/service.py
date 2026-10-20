from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.counterparty.config import CounterpartyConfig
from apps.services.counterparty.repository import find_card, find_graph
from shared.contracts.schemas import CounterpartyContext


class CounterpartyAggregates:
    def __init__(
        self, sessions: async_sessionmaker[AsyncSession], config: CounterpartyConfig
    ) -> None:
        self._sessions = sessions
        self._config = config

    async def context(
        self, client_id: str, beneficiary_id: str | None, inn: str | None
    ) -> CounterpartyContext:
        if beneficiary_id is None:
            return self._unknown()
        async with self._sessions() as session:
            card = await find_card(session, beneficiary_id)
            graph = await find_graph(session, client_id)
        if card is None and (graph is None or beneficiary_id not in graph.payload["dependence"]):
            return self._unknown()
        segment = card.industry_class if card else self._config.no_card_segment
        payload = graph.payload if graph else None
        dependence = payload["dependence"].get(beneficiary_id) if payload else None
        return CounterpartyContext(
            industry_class=card.industry_class if card else None,
            region=card.region if card else None,
            size_bucket=card.size_bucket if card else None,
            share_of_client_outflow=(
                payload["outflow_segments"].get(segment, 0.0) if payload else None
            ),
            share_of_counterparty_inflow=dependence,
            confidence=self._confidence(card is not None, dependence is not None),
        )

    def _confidence(self, has_card: bool, is_paid: bool) -> float:
        if not has_card:
            return self._config.confidence.low
        return self._config.confidence.linked if is_paid else self._config.confidence.card_only

    def _unknown(self) -> CounterpartyContext:
        return CounterpartyContext(
            industry_class=None,
            region=None,
            size_bucket=None,
            share_of_client_outflow=None,
            share_of_counterparty_inflow=None,
            confidence=self._config.confidence.low,
        )
