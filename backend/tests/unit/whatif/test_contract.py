import pytest

from apps.services import whatif
from shared.contracts.ports import WhatIfService
from shared.di.container import Container


def resolve() -> WhatIfService:
    container = Container()
    whatif.register(container)
    return container.resolve(WhatIfService)


def test_implements_port() -> None:
    assert isinstance(resolve(), WhatIfService)


async def test_methods_point_to_implementing_task() -> None:
    with pytest.raises(NotImplementedError, match="AH-24"):
        await resolve().rate_burden(1.0, 14.0, 13.5, 12)
