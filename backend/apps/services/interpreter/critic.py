from shared.contracts.schemas import HouseViewClaim, InsightCard, NewsItem


class CriticAgent:
    async def review(
        self, card: InsightCard, house_view: list[HouseViewClaim], news: list[NewsItem]
    ) -> list[str]:
        raise NotImplementedError("AH-22")
