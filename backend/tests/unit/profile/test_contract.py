import pytest

from apps.services import profile
from shared.contracts.ports import ProfileService
from shared.di.container import Container


def resolve() -> ProfileService:
    container = Container()
    profile.register(container)
    return container.resolve(ProfileService)


def test_implements_port() -> None:
    assert isinstance(resolve(), ProfileService)


async def test_methods_point_to_implementing_task() -> None:
    with pytest.raises(NotImplementedError, match="AH-7"):
        await resolve().list_clients("user")
