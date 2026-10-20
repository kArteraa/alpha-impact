from apps.services.products.service import ProductCatalog
from shared.contracts.ports import ProductRulesService
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    container.register(ProductRulesService, lambda _: ProductCatalog())
