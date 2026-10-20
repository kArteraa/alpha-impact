from apps.services import products
from shared.contracts.ports import ProductRulesService
from shared.contracts.schemas import ProductOffer
from shared.di.container import Container
from tests.unit.products.profiles import make_profile


def resolve() -> ProductRulesService:
    container = Container()
    products.register(container)
    return container.resolve(ProductRulesService)


def test_implements_port() -> None:
    assert isinstance(resolve(), ProductRulesService)


async def test_match_returns_offer_through_port() -> None:
    offer = await resolve().match(make_profile({"imports": True}), "fx", ["ruble_weakening"])

    assert isinstance(offer, ProductOffer)
