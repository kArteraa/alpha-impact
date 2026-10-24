from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import HTTPException, Request, Response, status
from fastapi.routing import APIRoute

from shared.contracts.errors import (
    AccessDenied,
    BudgetExceeded,
    ChargedModelError,
    DomainError,
    NotFound,
)

STATUS_BY_ERROR: tuple[tuple[type[DomainError], int], ...] = (
    (AccessDenied, status.HTTP_403_FORBIDDEN),
    (NotFound, status.HTTP_404_NOT_FOUND),
    (BudgetExceeded, status.HTTP_503_SERVICE_UNAVAILABLE),
    (ChargedModelError, status.HTTP_503_SERVICE_UNAVAILABLE),
    (DomainError, status.HTTP_422_UNPROCESSABLE_CONTENT),
)

Handler = Callable[[Request], Coroutine[Any, Any, Response]]


class DomainErrorRoute(APIRoute):
    def get_route_handler(self) -> Handler:
        handler = super().get_route_handler()

        async def guarded(request: Request) -> Response:
            try:
                return await handler(request)
            except DomainError as error:
                code = next(code for kind, code in STATUS_BY_ERROR if isinstance(error, kind))
                raise HTTPException(code, str(error)) from error

        return guarded
