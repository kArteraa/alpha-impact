from apps.services.news.service import NewsIndex, PageClassifier
from shared.contracts.ports import NewsService, PageContextService
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(NewsService, lambda _: NewsIndex())
    container.register(PageContextService, lambda _: PageClassifier())
