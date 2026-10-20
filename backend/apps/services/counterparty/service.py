from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.counterparty.config import CounterpartyConfig
from apps.services.counterparty.graph import CardFields, card_aggregates, segment
from apps.services.counterparty.repository import find_card, find_flows
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
        card: CardFields | None = None
        flows: tuple[float, float | None] | None = None
        if beneficiary_id is not None:
            async with self._sessions() as session:
                card = await find_card(session, beneficiary_id)
                flows = await find_flows(
                    session, client_id, beneficiary_id, segment(card, self._config)
                )
        segment_share, dependence = flows if flows else (None, None)
        if card is None and dependence is None:
            segment_share = None
        return CounterpartyContext(
            **card_aggregates(card),
            share_of_client_outflow=segment_share,
            share_of_counterparty_inflow=dependence,
            confidence=self._confidence(card is not None, dependence is not None),
        )

    def _confidence(self, has_card: bool, is_paid: bool) -> float:
        if not has_card:
            return self._config.confidence.low
        return self._config.confidence.linked if is_paid else self._config.confidence.card_only
