import pytest

from apps.services import products
from shared.contracts.ports import ProductRulesService
from shared.contracts.schemas import ClientProfile
from shared.di.container import Container


def resolve() -> ProductRulesService:
    container = Container()
    products.register(container)
    return container.resolve(ProductRulesService)


def test_implements_port() -> None:
    assert isinstance(resolve(), ProductRulesService)


async def test_match_points_to_task() -> None:
    profile = ClientProfile(
        client_id="c",
        group_id=None,
        group_members=[],
        features={},
        exposures={},
        flags={},
        version=1,
    )
    with pytest.raises(NotImplementedError, match="AH-25"):
        await resolve().match(profile, "payment", [])
