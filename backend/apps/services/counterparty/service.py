from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from apps.services.counterparty.config import CounterpartyConfig
from apps.services.counterparty.graph import card_aggregates, segment
from apps.services.counterparty.repository import Found, find_counterparty
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
        found: Found | None = None
        if beneficiary_id is not None and beneficiary_id != client_id:
            async with self._sessions() as session:
                found = await find_counterparty(session, client_id, beneficiary_id)
        card, segments, dependence = found if found else (None, None, None)
        segment_share = None
        if segments is not None and (card is not None or dependence is not None):
            segment_share = segments.get(segment(card, self._config), 0.0)
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
