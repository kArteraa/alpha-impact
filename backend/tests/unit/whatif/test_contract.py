from apps.services import whatif
from shared.contracts.ports import WhatIfService
from shared.contracts.schemas import WhatIfResult
from shared.di.container import Container


def resolve() -> WhatIfService:
    container = Container()
    whatif.register(container)
    return container.resolve(WhatIfService)


def test_implements_port() -> None:
    assert isinstance(resolve(), WhatIfService)


async def test_port_methods_return_results() -> None:
    service = resolve()

    results = [
        await service.rate_burden(100_000_000.0, 14.0, 13.5, 12),
        await service.deposit_terms(50_000_000.0, 90, [14.0, 13.5, 13.0]),
        await service.fx_exposure(1_000_000.0, "USD", 82.0, 87.0),
    ]

    assert [r.kind for r in results] == ["rate_burden", "deposit_terms", "fx_exposure"]
    assert all(isinstance(r, WhatIfResult) for r in results)
