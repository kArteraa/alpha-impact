from datetime import date

from shared.contracts.schemas import Factor, NewsItem, PageContext


class NewsIndex:
    async def search(
        self,
        factors: list[str],
        industry: str | None,
        region: str | None,
        country: str | None,
        since: date,
        limit: int = 10,
    ) -> list[NewsItem]:
        raise NotImplementedError("AH-13")

    async def annotate(self, title: str, text: str, url: str) -> NewsItem:
        raise NotImplementedError("AH-13")


class PageClassifier:
    async def classify(self, page: PageContext) -> tuple[str, list[str], list[Factor]]:
        raise NotImplementedError("AH-30")
