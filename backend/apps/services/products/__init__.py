from apps.services.products.catalog import RULES_PATH, load_catalog
from apps.services.products.service import ProductCatalog
from shared.contracts.ports import ProductRulesService
from shared.di.container import Container

__all__ = ["register"]


def register(container: Container) -> None:
    catalog = ProductCatalog(load_catalog(RULES_PATH))
    container.register(ProductRulesService, lambda _: catalog)
